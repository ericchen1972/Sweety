from pathlib import Path

from PIL import Image, ImageOps


GENERATED = Path.home() / ".codex/generated_images/019f8743-babc-7652-b9ba-e9b204cd2ebe"
OUTPUT = Path(__file__).resolve().parents[2] / "web/images/personas"
SOURCES = {
    "careful-bank-operations-specialist.jpg": "exec-7ba5c881-9bfe-498f-817e-846f8ef5765e.png",
    "busy-bakery-owner.jpg": "exec-18578001-1425-4102-aae0-401a2614814c.png",
    "guarded-insurance-clerk.jpg": "exec-6a315803-f144-485f-aecd-2d1301c8cd08.png",
    "practical-taxi-driver.jpg": "exec-7e32f215-411e-46bf-9052-203c40c4e139.png",
    "factory-shift-supervisor.jpg": "exec-5627eb5d-9659-4448-a6d4-d8bdc0f38cfc.png",
    "independent-repair-technician.jpg": "exec-a072300d-c619-41fb-8120-d0ba3c8a21c3.png",
    "careful-community-pharmacist.jpg": "exec-1a98efa0-5134-4f27-9ce2-38580e109d64.png",
    "busy-market-stall-owner.jpg": "exec-50122748-1f1f-48e3-a928-26e042534f80.png",
    "retired-school-administrator.jpg": "exec-0871041c-af6c-4aae-be8d-cab724bc45bf.png",
    "practical-hardware-store-owner.jpg": "exec-4df7ec70-510f-4bfd-b5d2-f030693b52b5.png",
    "apartment-building-manager.jpg": "exec-2984d14c-32be-4a16-9b4a-89172123991e.png",
    "semi-retired-logistics-dispatcher.jpg": "exec-d2cee7e5-4779-4079-97c6-e6cf0c63f911.png",
    "careful-retired-nurse.jpg": "exec-9f35b316-3fce-45ae-922a-a36b23eebee8.png",
    "active-community-volunteer.jpg": "exec-8be4593f-492c-4b6d-8d32-286ce9fbdb64.png",
    "frugal-retired-bookkeeper.jpg": "exec-163a6401-adf9-480c-a638-65ccd8ad50f1.png",
    "retired-plumber.jpg": "exec-d0bc264e-31d9-4dad-a588-e7c295b906a5.png",
    "traditional-tea-shop-owner.jpg": "exec-4c13e8d0-ef42-4b1c-b6b2-5479d689f7ec.png",
    "retired-intercity-bus-driver.jpg": "exec-2ebfad46-c0a5-44e2-a26a-f40f92ef9fc2.png",
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for output_name, source_name in SOURCES.items():
        source = GENERATED / source_name
        if not source.exists():
            raise FileNotFoundError(source)
        with Image.open(source) as image:
            prepared = ImageOps.fit(
                image.convert("RGB"),
                (1280, 720),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            destination = OUTPUT / output_name
            prepared.save(destination, "JPEG", quality=90, optimize=True)
            print(f"{output_name}: {prepared.size[0]}x{prepared.size[1]}")


if __name__ == "__main__":
    main()
