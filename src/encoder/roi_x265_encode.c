/*
 * roi_x265_encode — x265 encoder with per-frame, per-block QP offset maps.
 *
 * Reads an 8-bit 4:2:0 Y4M file and encodes it to a raw HEVC (Annex-B)
 * bitstream with libx265. When a QP map (.qpm) is given, each frame gets a
 * float QP offset per 16x16 block through x265_picture.quantOffsets.
 * Negative offsets = finer quantization = more bits.
 *
 * Rate control is 2-pass ABR by default, both passes run in one invocation
 * with identical maps (x265: "Behavior if quant offsets differ between
 * encoding passes is undefined"). Run without --qpmap for the matched
 * baseline: everything else stays identical.
 *
 * QP map file format (.qpm, little-endian):
 *   char[4]  magic   = "QPM1"
 *   int32    block   = 16            (block size in pixels)
 *   int32    cols    = ceil(W/16)
 *   int32    rows    = ceil(H/16)
 *   int32    nframes                 (must be >= frames encoded)
 *   float32  data[nframes][rows][cols]   (row-major, QP offsets)
 */

#define _FILE_OFFSET_BITS 64
#define _CRT_SECURE_NO_WARNINGS
#define _CRT_NONSTDC_NO_WARNINGS
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <x265.h>

/* 64-bit file positions (Y4M files are often > 2 GB) */
typedef long long foff;
#if defined(_WIN32)
#  define FSEEK(f, o, w) _fseeki64((f), (o), (w))
#  define FTELL(f) _ftelli64(f)
#else
#  define FSEEK(f, o, w) fseeko((f), (off_t)(o), (w))
#  define FTELL(f) ((foff)ftello(f))
#endif

#define DIE(...) do { fprintf(stderr, "error: " __VA_ARGS__); fputc('\n', stderr); exit(1); } while (0)

/* ------------------------------------------------------------------ */
/* Options                                                             */
/* ------------------------------------------------------------------ */

typedef struct {
    const char *input, *output, *qpmap, *preset, *tune, *x265_params;
    const char *stats, *summary;
    int bitrate_kbps, passes, max_frames, keep_stats;
} Opts;

static void usage(void)
{
    fprintf(stderr,
        "usage: roi_x265_encode -i in.y4m -o out.hevc --bitrate KBPS [options]\n"
        "\n"
        "  -i, --input FILE        8-bit 4:2:0 Y4M input\n"
        "  -o, --output FILE       raw HEVC Annex-B output (.hevc)\n"
        "  --bitrate KBPS          target bitrate in kbit/s (ABR)\n"
        "  --qpmap FILE            per-frame QP offset map (.qpm); omit for baseline\n"
        "  --passes 1|2            rate-control passes (default 2)\n"
        "  --preset NAME           x265 preset (default medium)\n"
        "  --tune NAME             x265 tune (default none)\n"
        "  --x265-params K=V:K=V   extra x265 options, applied after defaults\n"
        "  --frames N              encode at most N frames\n"
        "  --stats FILE            2-pass stats file (default <output>.x265stats)\n"
        "  --keep-stats            keep the stats files after encoding\n"
        "  --summary FILE          write a JSON summary (bitrate, frames, settings)\n");
    exit(1);
}

static void parse_args(int argc, char **argv, Opts *o)
{
    memset(o, 0, sizeof *o);
    o->preset = "medium";
    o->passes = 2;
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
#define NEXT() ((i + 1 < argc) ? argv[++i] : (usage(), (char *)NULL))
        if (!strcmp(a, "-i") || !strcmp(a, "--input")) o->input = NEXT();
        else if (!strcmp(a, "-o") || !strcmp(a, "--output")) o->output = NEXT();
        else if (!strcmp(a, "--bitrate")) o->bitrate_kbps = atoi(NEXT());
        else if (!strcmp(a, "--qpmap")) o->qpmap = NEXT();
        else if (!strcmp(a, "--passes")) o->passes = atoi(NEXT());
        else if (!strcmp(a, "--preset")) o->preset = NEXT();
        else if (!strcmp(a, "--tune")) o->tune = NEXT();
        else if (!strcmp(a, "--x265-params")) o->x265_params = NEXT();
        else if (!strcmp(a, "--frames")) o->max_frames = atoi(NEXT());
        else if (!strcmp(a, "--stats")) o->stats = NEXT();
        else if (!strcmp(a, "--keep-stats")) o->keep_stats = 1;
        else if (!strcmp(a, "--summary")) o->summary = NEXT();
        else if (!strcmp(a, "-h") || !strcmp(a, "--help")) usage();
        else { fprintf(stderr, "unknown option: %s\n", a); usage(); }
#undef NEXT
    }
    if (!o->input || !o->output || o->bitrate_kbps <= 0) usage();
    if (o->passes != 1 && o->passes != 2) DIE("--passes must be 1 or 2");
}

/* ------------------------------------------------------------------ */
/* Y4M input (8-bit 4:2:0 only)                                        */
/* ------------------------------------------------------------------ */

typedef struct {
    FILE *f;
    int w, h, cw, ch, fps_num, fps_den;
    foff first_frame;      /* file offset of the first FRAME line */
    size_t frame_bytes;
    int nframes;            /* frames in the file */
} Y4M;

static void y4m_open(const char *path, Y4M *y)
{
    memset(y, 0, sizeof *y);
    y->f = fopen(path, "rb");
    if (!y->f) DIE("cannot open %s: %s", path, strerror(errno));

    char line[4096];
    if (!fgets(line, sizeof line, y->f) || strncmp(line, "YUV4MPEG2 ", 10))
        DIE("%s is not a Y4M file", path);

    char chroma[64] = "420";
    y->fps_den = 1;
    for (char *t = strtok(line + 10, " \n"); t; t = strtok(NULL, " \n")) {
        switch (t[0]) {
        case 'W': y->w = atoi(t + 1); break;
        case 'H': y->h = atoi(t + 1); break;
        case 'F': sscanf(t + 1, "%d:%d", &y->fps_num, &y->fps_den); break;
        case 'C': snprintf(chroma, sizeof chroma, "%s", t + 1); break;
        default: break;
        }
    }
    if (y->w <= 0 || y->h <= 0 || y->fps_num <= 0 || y->fps_den <= 0)
        DIE("bad Y4M header (W/H/F missing)");
    if (strcmp(chroma, "420") && strcmp(chroma, "420jpeg") &&
        strcmp(chroma, "420mpeg2") && strcmp(chroma, "420paldv"))
        DIE("only 8-bit 4:2:0 Y4M is supported (got C%s); convert with "
            "ffmpeg -pix_fmt yuv420p", chroma);
    if ((y->w & 1) || (y->h & 1)) DIE("width and height must be even");

    y->cw = (y->w + 1) / 2;
    y->ch = (y->h + 1) / 2;
    y->frame_bytes = (size_t)y->w * y->h + 2 * (size_t)y->cw * y->ch;
    y->first_frame = FTELL(y->f);

    /* count complete frames so 2-pass rate control knows the total */
    FSEEK(y->f, 0, SEEK_END);
    foff size = FTELL(y->f);
    FSEEK(y->f, y->first_frame, SEEK_SET);
    while (fgets(line, sizeof line, y->f)) {
        if (strncmp(line, "FRAME", 5)) DIE("corrupt Y4M: expected FRAME at frame %d", y->nframes);
        foff next = FTELL(y->f) + (foff)y->frame_bytes;
        if (next > size) break;                  /* truncated last frame */
        y->nframes++;
        FSEEK(y->f, next, SEEK_SET);
    }
    FSEEK(y->f, y->first_frame, SEEK_SET);
}

static int y4m_read(Y4M *y, uint8_t *buf)
{
    char line[256];
    if (!fgets(line, sizeof line, y->f)) return 0;
    if (strncmp(line, "FRAME", 5)) DIE("corrupt Y4M frame header");
    return fread(buf, 1, y->frame_bytes, y->f) == y->frame_bytes;
}

/* ------------------------------------------------------------------ */
/* QP map input                                                        */
/* ------------------------------------------------------------------ */

typedef struct {
    FILE *f;
    int32_t block, cols, rows, nframes;
    size_t frame_floats;
} QPMap;

static void qpmap_open(const char *path, QPMap *m, const Y4M *y)
{
    memset(m, 0, sizeof *m);
    m->f = fopen(path, "rb");
    if (!m->f) DIE("cannot open %s: %s", path, strerror(errno));
    char magic[4];
    int32_t hdr[4];
    if (fread(magic, 1, 4, m->f) != 4 || memcmp(magic, "QPM1", 4))
        DIE("%s is not a QPM1 map", path);
    if (fread(hdr, sizeof(int32_t), 4, m->f) != 4) DIE("truncated map header");
    m->block = hdr[0]; m->cols = hdr[1]; m->rows = hdr[2]; m->nframes = hdr[3];

    int want_cols = (y->w + 15) / 16, want_rows = (y->h + 15) / 16;
    if (m->block != 16) DIE("map block size %d unsupported (need 16)", m->block);
    if (m->cols != want_cols || m->rows != want_rows)
        DIE("map is %dx%d blocks but %dx%d video needs %dx%d",
            m->cols, m->rows, y->w, y->h, want_cols, want_rows);
    m->frame_floats = (size_t)m->cols * m->rows;
}

static void qpmap_rewind(QPMap *m) { FSEEK(m->f, 20, SEEK_SET); }

static void qpmap_read(QPMap *m, float *dst, int frame)
{
    if (frame >= m->nframes) DIE("map has %d frames but frame %d was requested", m->nframes, frame);
    if (fread(dst, sizeof(float), m->frame_floats, m->f) != m->frame_floats)
        DIE("truncated map at frame %d", frame);
}

/* ------------------------------------------------------------------ */
/* Encoder parameters                                                  */
/* ------------------------------------------------------------------ */

static void set_param(x265_param *p, const char *k, const char *v)
{
    int r = x265_param_parse(p, k, v);
    if (r == X265_PARAM_BAD_NAME) DIE("unknown x265 option '%s'", k);
    if (r == X265_PARAM_BAD_VALUE) DIE("bad value '%s' for x265 option '%s'", v, k);
}

static char *dupstr(const char *s)        /* strdup isn't standard C */
{
    size_t n = strlen(s) + 1;
    char *d = malloc(n);
    if (!d) DIE("out of memory");
    return memcpy(d, s, n);
}

static void apply_user_params(x265_param *p, const char *s)
{
    if (!s || !*s) return;
    char *copy = dupstr(s);
    for (char *kv = strtok(copy, ":"); kv; kv = strtok(NULL, ":")) {
        char *eq = strchr(kv, '=');
        if (eq) { *eq = 0; set_param(p, kv, eq + 1); }
        else set_param(p, kv, "1");          /* bare flag, e.g. "no-sao" */
    }
    free(copy);
}

static x265_param *make_param(const Opts *o, const Y4M *y, int frames, int pass, const char *stats)
{
    x265_param *p = x265_param_alloc();
    if (!p) DIE("x265_param_alloc failed");
    if (x265_param_default_preset(p, o->preset, o->tune) < 0)
        DIE("bad preset/tune '%s'/'%s'", o->preset, o->tune ? o->tune : "");

    p->sourceWidth  = y->w;
    p->sourceHeight = y->h;
    p->fpsNum       = (uint32_t)y->fps_num;
    p->fpsDenom     = (uint32_t)y->fps_den;
    p->internalCsp  = X265_CSP_I420;
    p->totalFrames  = frames;

    char buf[64];
    snprintf(buf, sizeof buf, "%d", o->bitrate_kbps);
    set_param(p, "bitrate", buf);      /* ABR */
    set_param(p, "qg-size", "16");     /* QP can change every 16x16 block */

    apply_user_params(p, o->x265_params);

    if (o->passes == 2) {
        set_param(p, "pass", pass == 1 ? "1" : "2");
        set_param(p, "stats", stats);
    }

    /* settings the offset maps depend on (see x265.h, slicetype.cpp) */
    if (p->rc.rateControlMode != X265_RC_ABR)
        DIE("rate control must be ABR (bitrate); --x265-params changed it");
    if (o->qpmap) {
        if (p->rc.aqMode == X265_AQ_NONE)
            DIE("x265 ignores quantOffsets when aq-mode=0; use aq-mode>=1 "
                "(aq-strength=0 applies the map alone)");
        if (p->rc.hevcAq)
            DIE("x265 ignores quantOffsets with hevc-aq; disable it");
        if (p->rc.qgSize != 16)
            DIE("this tool supports qg-size=16 only (got %d)", p->rc.qgSize);
    }
    return p;
}

/* ------------------------------------------------------------------ */
/* One encoding pass                                                   */
/* ------------------------------------------------------------------ */

typedef struct {
    uint64_t bytes;
    int frames;
    double off_sum, off_min, off_max;
    uint64_t off_count, off_neg;
} PassResult;

static uint64_t write_nals(FILE *out, x265_nal *nal, uint32_t n)
{
    uint64_t bytes = 0;
    for (uint32_t i = 0; i < n; i++) {
        if (out && fwrite(nal[i].payload, 1, nal[i].sizeBytes, out) != nal[i].sizeBytes)
            DIE("write failed: %s", strerror(errno));
        bytes += nal[i].sizeBytes;
    }
    return bytes;
}

static PassResult run_pass(const Opts *o, Y4M *y, QPMap *m, int frames, int pass, const char *stats, FILE *out)
{
    PassResult r = { 0 };
    r.off_min = INFINITY;
    r.off_max = -INFINITY;

    x265_param *p = make_param(o, y, frames, pass, stats);
    x265_encoder *enc = x265_encoder_open(p);
    if (!enc) DIE("x265_encoder_open failed (pass %d)", pass);

    x265_picture *pic = x265_picture_alloc();
    x265_picture_init(p, pic);
    pic->colorSpace = X265_CSP_I420;
    pic->bitDepth   = 8;

    uint8_t *buf = malloc(y->frame_bytes);
    float *offsets = m ? malloc(m->frame_floats * sizeof(float)) : NULL;
    if (!buf || (m && !offsets)) DIE("out of memory");

    pic->planes[0] = buf;
    pic->planes[1] = buf + (size_t)y->w * y->h;
    pic->planes[2] = (uint8_t *)pic->planes[1] + (size_t)y->cw * y->ch;
    pic->stride[0] = y->w;
    pic->stride[1] = pic->stride[2] = y->cw;

    x265_nal *nal;
    uint32_t nnal;
    if (x265_encoder_headers(enc, &nal, &nnal) < 0) DIE("x265_encoder_headers failed");
    r.bytes += write_nals(out, nal, nnal);

    FSEEK(y->f, y->first_frame, SEEK_SET);
    if (m) qpmap_rewind(m);

    for (int i = 0; i < frames; i++) {
        if (!y4m_read(y, buf)) DIE("could not read frame %d", i);
        pic->pts = i;
        /* ROI encodes must pass a map for EVERY frame (x265 reuses frame
         * buffers and only allocates offset storage if the first frames had
         * one); zeros mean "no change". Baseline passes NULL for every frame. */
        pic->quantOffsets = NULL;
        if (m) {
            qpmap_read(m, offsets, i);
            for (size_t k = 0; k < m->frame_floats; k++) {
                double v = offsets[k];
                if (!isfinite(v)) DIE("non-finite offset in map frame %d", i);
                r.off_sum += v; r.off_count++;
                if (v < 0) r.off_neg++;
                if (v < r.off_min) r.off_min = v;
                if (v > r.off_max) r.off_max = v;
            }
            pic->quantOffsets = offsets;   /* copied by x265 during the call */
        }
        int ret = x265_encoder_encode(enc, &nal, &nnal, pic, NULL);
        if (ret < 0) DIE("encode failed at frame %d", i);
        r.bytes += write_nals(out, nal, nnal);
    }
    for (;;) {                                   /* flush delayed frames */
        int ret = x265_encoder_encode(enc, &nal, &nnal, NULL, NULL);
        if (ret < 0) DIE("encode failed while flushing");
        r.bytes += write_nals(out, nal, nnal);
        if (ret == 0) break;
    }
    r.frames = frames;

    x265_encoder_close(enc);
    x265_picture_free(pic);
    x265_param_free(p);
    free(buf);
    free(offsets);
    return r;
}

/* ------------------------------------------------------------------ */
/* JSON summary helpers (escape so Windows paths stay valid JSON)       */
/* ------------------------------------------------------------------ */

static void json_string(FILE *s, const char *v)
{
    fputc('"', s);
    for (const unsigned char *p = (const unsigned char *)v; *p; p++) {
        if (*p == '"' || *p == '\\') fprintf(s, "\\%c", *p);
        else if (*p < 0x20) fprintf(s, "\\u%04x", *p);
        else fputc(*p, s);
    }
    fputc('"', s);
}

static void json_field(FILE *s, const char *key, const char *v)
{
    fprintf(s, "  \"%s\": ", key);
    json_string(s, v);
    fprintf(s, ",\n");
}

/* ------------------------------------------------------------------ */

int main(int argc, char **argv)
{
    Opts o;
    parse_args(argc, argv, &o);

    Y4M y;
    y4m_open(o.input, &y);
    int frames = y.nframes;
    if (o.max_frames > 0 && o.max_frames < frames) frames = o.max_frames;
    if (frames <= 0) DIE("no frames in %s", o.input);

    QPMap map, *m = NULL;
    if (o.qpmap) {
        qpmap_open(o.qpmap, &map, &y);
        if (map.nframes < frames) DIE("map has %d frames, need %d", map.nframes, frames);
        m = &map;
    }

    char stats_buf[4096];
    const char *stats = o.stats;
    if (!stats) {
        snprintf(stats_buf, sizeof stats_buf, "%s.x265stats", o.output);
        stats = stats_buf;
    }

    fprintf(stderr, "roi_x265_encode: %dx%d @ %d/%d fps, %d frames, %d kbps, %d pass(es), %s\n",
            y.w, y.h, y.fps_num, y.fps_den, frames, o.bitrate_kbps, o.passes,
            m ? o.qpmap : "no QP map (baseline)");

    PassResult r = { 0 };
    for (int pass = 1; pass <= o.passes; pass++) {
        int final = (pass == o.passes);
        FILE *out = NULL;
        if (final) {
            out = fopen(o.output, "wb");
            if (!out) DIE("cannot open %s: %s", o.output, strerror(errno));
        }
        fprintf(stderr, "--- pass %d/%d ---\n", pass, o.passes);
        r = run_pass(&o, &y, m, frames, pass, stats, out);
        if (out) fclose(out);
    }

    if (o.passes == 2 && !o.keep_stats) {
        char cutree[4200];
        snprintf(cutree, sizeof cutree, "%s.cutree", stats);
        remove(stats);
        remove(cutree);
    }

    double seconds = frames * (double)y.fps_den / y.fps_num;
    double kbps = r.bytes * 8.0 / seconds / 1000.0;
    double err = 100.0 * (kbps - o.bitrate_kbps) / o.bitrate_kbps;
    fprintf(stderr, "result: %llu bytes, %.3f s, %.2f kbps (target %d, %+.2f%%)\n",
            (unsigned long long)r.bytes, seconds, kbps, o.bitrate_kbps, err);
    if (m)
        fprintf(stderr, "map: mean offset %+.3f, min %+.2f, max %+.2f, %.1f%% of blocks negative\n",
                r.off_sum / r.off_count, r.off_min, r.off_max, 100.0 * r.off_neg / r.off_count);

    if (o.summary) {
        FILE *s = fopen(o.summary, "w");
        if (!s) DIE("cannot open %s", o.summary);
        fprintf(s, "{\n");
        json_field(s, "input", o.input);
        json_field(s, "output", o.output);
        if (m) json_field(s, "qpmap", o.qpmap);
        else fprintf(s, "  \"qpmap\": null,\n");
        fprintf(s, "  \"width\": %d,\n  \"height\": %d,\n", y.w, y.h);
        fprintf(s, "  \"fps_num\": %d,\n  \"fps_den\": %d,\n", y.fps_num, y.fps_den);
        fprintf(s, "  \"frames\": %d,\n  \"seconds\": %.6f,\n", frames, seconds);
        fprintf(s, "  \"bytes\": %llu,\n", (unsigned long long)r.bytes);
        fprintf(s, "  \"kbps\": %.4f,\n  \"target_kbps\": %d,\n", kbps, o.bitrate_kbps);
        fprintf(s, "  \"passes\": %d,\n", o.passes);
        json_field(s, "preset", o.preset);
        json_field(s, "x265_params", o.x265_params ? o.x265_params : "");
        if (m)
            fprintf(s, "  \"map_mean_offset\": %.6f,\n  \"map_min\": %.4f,\n  \"map_max\": %.4f,\n"
                       "  \"map_negative_fraction\": %.6f,\n",
                    r.off_sum / r.off_count, r.off_min, r.off_max, (double)r.off_neg / r.off_count);
        fprintf(s, "  \"x265_version\": ");
        json_string(s, x265_version_str);
        fprintf(s, "\n}\n");
        fclose(s);
    }

    fclose(y.f);
    if (m) fclose(m->f);
    x265_cleanup();
    return 0;
}
