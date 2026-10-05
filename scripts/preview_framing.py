"""Aperçu des cadrages.

Usage : python scripts/preview_framing.py DOSSIER_SORTIE RATIO page1.jpg [page2.jpg ...]
Si page1.json existe à côté de l'image, il est lu comme dict de page
(clé "focus_regions" ou "focus"), sinon le découpage automatique est utilisé.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services import video  # noqa: E402


def main() -> None:
    out_dir, ratio, sources = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
    out_dir.mkdir(parents=True, exist_ok=True)
    for src in map(Path, sources):
        frame = video._open_frame(src)
        sidecar = src.with_suffix(".json")
        page = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
        for number, rect in enumerate(video._regions_for_page(frame, page, ratio), start=1):
            box = video._crop_box(frame.width, frame.height, ratio, rect)
            still = video._still(frame, rect, ratio, out_dir)
            target = out_dir / f"{src.stem}_{number}.png"
            still.replace(target)
            print(f"{src.name} plan {number}: focus={tuple(round(v) for v in rect)} crop={box}")


if __name__ == "__main__":
    main()
