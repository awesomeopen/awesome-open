set -e
src=tmp/awesome-open-cat-logos; out=site/domains
for f in $src/*.png; do
  n=$(basename "$f" .png)
  w=$(magick identify -format %w "$f")
  L=$(( (w*33+50)/100 )); M=$(( (L+1)/2 )); S=$(( (M+1)/2 ))
  for pair in "l:$L" "m:$M" "s:$S"; do
    magick "$f" -filter Lanczos -distort Resize "${pair#*:}" \
      -channel RGB -unsharp 0x0.7+0.7+0.015 +channel \
      -define webp:method=6 -define webp:alpha-quality=100 -quality 88 \
      "$out/$n-${pair%%:*}.webp"
  done
done
