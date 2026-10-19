# Reuse the existing compatible project environment; source this before orbit work.
source /workspace/data/20261016/scripts/activate310.sh
export XDG_CONFIG_HOME=/workspace/data/20261016/.config
for _orbit_path in "$XDG_CONFIG_HOME/astropy" "$XDG_CACHE_HOME/astropy"; do
    case "$(realpath -m "$_orbit_path")" in
        /workspace/data/20261016/*) mkdir -p "$_orbit_path" ;;
        *) echo 'Astropy path outside project' >&2; return 1 ;;
    esac
done
unset _orbit_path
