# Commands

## Copy from windows to wsl

Run on WSL:

```code
cp /mnt/c/Users/shaki/Research/Multi-view Streaming/Video Samples/1080@60fps/one_piece.mp4 ~/roi-x265/videos/
```

## Copy files to windows

Run on WSL:

```code
cp baseline.mp4 box.mp4 compare.mp4 compare_box.mp4 /mnt/c/Users/$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')/Videos/
```
