#!/usr/bin/env bash
# Check that every macOS wheel in a directory carries a library built for the
# architecture its filename claims, and for no older macOS than the tag allows.
#
#   check_macos_wheel_arch.sh <wheelhouse>
#
# The x86_64 wheels are cross-compiled on an arm64 runner, where a build that
# ignored ARCHFLAGS would quietly produce an arm64 library inside an
# x86_64-tagged wheel. pip would install it on an Intel Mac and the import would
# then fail to load the library, so catch that here instead.
set -euo pipefail

dir="${1:?usage: $0 <wheelhouse>}"
shopt -s nullglob
wheels=("$dir"/*macosx*.whl)
if [ "${#wheels[@]}" -eq 0 ]; then
  echo "No macOS wheels found in $dir"; exit 1
fi

failed=0
for whl in "${wheels[@]}"; do
  name=$(basename "$whl" .whl)
  plat=${name##*-}                       # e.g. macosx_10_13_x86_64
  tag_arch=$(echo "$plat" | sed -E 's/^macosx_[0-9]+_[0-9]+_//')
  tag_min=$(echo "$plat" | sed -E 's/^macosx_([0-9]+)_([0-9]+)_.*/\1.\2/')
  case "$tag_arch" in
    universal2) want="arm64 x86_64" ;;
    x86_64|arm64) want="$tag_arch" ;;
    *) echo "FAIL $name: unexpected platform tag $plat"; failed=1; continue ;;
  esac

  tmp=$(mktemp -d)
  unzip -q "$whl" -d "$tmp"
  libs=$(find "$tmp" -name '*.dylib')
  if [ -z "$libs" ]; then
    echo "FAIL $name: no .dylib inside the wheel"; failed=1; rm -rf "$tmp"; continue
  fi
  while IFS= read -r lib; do
    got=$(lipo -archs "$lib" | tr ' ' '\n' | sort | xargs)
    minos=$(otool -l "$lib" | awk '/LC_BUILD_VERSION/{b=1} b&&/minos/{print $2; exit} /LC_VERSION_MIN_MACOSX/{v=1} v&&/version/{print $2; exit}')
    rel=${lib#"$tmp"/}
    if [ "$got" != "$want" ]; then
      echo "FAIL $name: $rel is [$got], tag says [$want]"; failed=1
    elif [ "$(printf '%s\n%s\n' "$minos" "$tag_min" | sort -V | tail -n1)" != "$tag_min" ]; then
      echo "FAIL $name: $rel needs macOS $minos, tag says $tag_min"; failed=1
    else
      echo "ok   $name: $rel is [$got], minos $minos ($(file -b "$lib"))"
    fi
  done <<< "$libs"
  rm -rf "$tmp"
done
exit "$failed"
