"""Product images: processing, rejection rules, the placeholder fallback,
file lifecycle, and the staff upload flow."""

from http import HTTPStatus
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from .images import prepare_product_image
from .models import Product

pytestmark = pytest.mark.django_db

RED = (255, 0, 0)
BLUE = (0, 0, 255)


def image_upload(
    name="photo.jpg", size=(1200, 1500), fmt="JPEG", mode="RGB", color=BLUE, **save
):
    """An in-memory image file, as a browser would upload it."""
    buffer = BytesIO()
    Image.new(mode, size, color).save(buffer, fmt, **save)
    return SimpleUploadedFile(name, buffer.getvalue())


def rejection(upload):
    with pytest.raises(ValidationError) as excinfo:
        prepare_product_image(upload)
    return excinfo.value.messages[0]


def give_image(product):
    """Attach a processed image to ``product``; return its storage name."""
    product.image = prepare_product_image(image_upload())
    product.save()
    return product.image.name


def stored(product_or_name):
    name = getattr(product_or_name, "name", product_or_name)
    return Product._meta.get_field("image").storage.exists(name)


# --- Processing -------------------------------------------------------------


def test_output_is_an_800_by_1000_webp(db):
    result = prepare_product_image(image_upload(size=(2400, 1800)))

    image = Image.open(result)
    assert image.format == "WEBP"
    assert image.size == (800, 1000)


def test_wide_images_are_center_cropped_not_letterboxed(db):
    # 2000×1000 → the 4:5 crop keeps the middle 800 columns: all blue.
    source = Image.new("RGB", (2000, 1000), RED)
    source.paste(BLUE, (550, 0, 1450, 1000))
    buffer = BytesIO()
    source.save(buffer, "PNG")

    image = Image.open(
        prepare_product_image(SimpleUploadedFile("wide.png", buffer.getvalue()))
    ).convert("RGB")

    for x in (2, 400, 797):
        r, g, b = image.getpixel((x, 500))
        assert b > 200 and r < 60, (x, (r, g, b))


def test_transparency_is_kept(db):
    upload = image_upload("cutout.png", fmt="PNG", mode="RGBA", color=(0, 0, 255, 0))

    image = Image.open(prepare_product_image(upload))

    assert image.mode == "RGBA"
    assert image.getpixel((400, 500))[3] == 0


def test_camera_orientation_is_applied(db):
    # Stored 1000×800 but tagged "rotate 90°": really an 800×1000 portrait,
    # which passes the size rule only once the rotation is applied.
    exif = Image.Exif()
    exif[0x0112] = 6
    upload = image_upload("phone.jpg", size=(1000, 800), exif=exif)

    assert Image.open(prepare_product_image(upload)).size == (800, 1000)


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_supported_formats_are_accepted(db, fmt):
    upload = image_upload(f"photo.{fmt.lower()}", fmt=fmt)

    assert Image.open(prepare_product_image(upload)).format == "WEBP"


# --- Rejection rules --------------------------------------------------------


def test_rejects_files_over_10_mb(db):
    upload = SimpleUploadedFile("huge.jpg", b"\xff" * (10 * 1024 * 1024 + 1))

    message = rejection(upload)

    assert "10 MB or smaller" in message
    assert "huge.jpg" in message


def test_rejects_files_that_are_not_images(db):
    message = rejection(SimpleUploadedFile("photo.jpg", b"definitely not a JPEG"))

    assert "couldn't read" in message
    assert "JPEG, PNG, or WebP" in message


def test_rejects_truncated_images(db):
    whole = image_upload().read()

    message = rejection(SimpleUploadedFile("cut.jpg", whole[: len(whole) // 2]))

    assert "couldn't read" in message


def test_rejects_decompression_bombs(db, monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)

    assert "couldn't read" in rejection(image_upload())


def test_rejects_heic_with_an_export_hint(db):
    heic = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 64

    message = rejection(SimpleUploadedFile("IMG_0042.HEIC", heic))

    assert "HEIC" in message
    assert "Export it as a JPEG" in message


def test_rejects_svg(db):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 5"></svg>'

    message = rejection(SimpleUploadedFile("logo.svg", svg))

    assert "SVG" in message
    assert "JPEG, PNG, or WebP" in message


def test_rejects_gif(db):
    message = rejection(image_upload("anim.gif", fmt="GIF", mode="P"))

    assert "GIF" in message
    assert "JPEG, PNG, or WebP" in message


def test_rejects_a_file_with_an_image_extension_but_another_format(db):
    # The extension says JPEG; the bytes say GIF. The bytes win.
    message = rejection(image_upload("sneaky.jpg", fmt="GIF", mode="P"))

    assert "GIF" in message


def test_rejects_images_too_small_after_the_crop(db):
    message = rejection(image_upload(size=(1600, 900)))

    # 1600×900 crops to 720×900: wide enough before, too small after.
    assert "1600×900" in message
    assert "720×900" in message
    assert "800×1000" in message


def test_accepts_the_smallest_wide_image_that_crops_large_enough(db):
    # MindSync Duo's shape: 1536×1024 crops to 819×1024.
    upload = image_upload(size=(1536, 1024))

    assert Image.open(prepare_product_image(upload)).size == (800, 1000)


# --- image_url: never a broken image ----------------------------------------


def test_image_url_is_the_placeholder_without_an_image(product):
    assert product.image_url == "/static/images/placeholders/home-assistants.svg"


def test_image_url_is_the_upload_when_stored(product):
    name = give_image(product)

    assert product.image_url == f"/media/{name}"


def test_image_url_falls_back_when_the_file_is_missing(product):
    product.image = "products/long-gone.webp"
    product.save()

    assert product.image_url == "/static/images/placeholders/home-assistants.svg"


def test_upload_names_are_unique_per_upload(product):
    first = give_image(product)
    second = give_image(product)

    assert first != second
    assert first.startswith("products/seraphine-home-hub-")
    assert first.endswith(".webp")


@pytest.mark.parametrize("page", ["catalog", "detail"])
def test_storefront_shows_the_image_or_placeholder(client, product, page):
    url = (
        reverse("products:catalog")
        if page == "catalog"
        else (product.get_absolute_url())
    )

    assert "placeholders/home-assistants.svg" in client.get(url).content.decode()

    name = give_image(product)

    html = client.get(url).content.decode()
    assert f"/media/{name}" in html
    assert "placeholders/home-assistants.svg" not in html


# --- File lifecycle ---------------------------------------------------------


def test_replacing_an_image_deletes_the_old_file(
    product, django_capture_on_commit_callbacks
):
    old = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        new = give_image(product)

    assert not stored(old)
    assert stored(new)


def test_clearing_an_image_deletes_its_file(
    product, django_capture_on_commit_callbacks
):
    old = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        product.image = ""
        product.save()

    assert not stored(old)


def test_saving_without_changing_the_image_keeps_it(
    product, django_capture_on_commit_callbacks
):
    name = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        product.price = 1
        product.save()

    assert stored(name)


def test_deleting_a_product_deletes_its_file(
    product, django_capture_on_commit_callbacks
):
    name = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        product.delete()

    assert not stored(name)


def test_bulk_deleting_products_deletes_their_files(
    product, django_capture_on_commit_callbacks
):
    # The seed command's wipe deletes by queryset, skipping Model.delete().
    name = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        Product.objects.all().delete()

    assert not stored(name)


def test_files_are_kept_until_the_transaction_commits(
    product, django_capture_on_commit_callbacks
):
    name = give_image(product)

    with django_capture_on_commit_callbacks() as callbacks:
        product.delete()
        assert stored(name)

    assert len(callbacks) == 1


# --- The staff upload flow --------------------------------------------------


def product_data(product, **overrides):
    data = {
        "name": product.name,
        "slug": product.slug,
        "price": str(product.price),
        "category": str(product.category.pk),
        "is_available": "on",
    }
    data.update(overrides)
    return data


def test_staff_can_upload_an_image(client, staff_user, product):
    client.force_login(staff_user)

    response = client.post(
        reverse("products:manage_product_update", kwargs={"pk": product.pk}),
        product_data(product, image=image_upload()),
    )

    assert response.status_code == HTTPStatus.FOUND
    product.refresh_from_db()
    assert product.image.name.endswith(".webp")
    assert Image.open(product.image).size == (800, 1000)


def test_staff_can_create_a_product_with_an_image(client, staff_user, category):
    client.force_login(staff_user)

    client.post(
        reverse("products:manage_product_create"),
        {
            "name": "MindSync Sleep Halo",
            "slug": "mindsync-sleep-halo",
            "price": "199.99",
            "category": str(category.pk),
            "image": image_upload(),
        },
    )

    product = Product.objects.get(slug="mindsync-sleep-halo")
    assert product.image.name.startswith("products/mindsync-sleep-halo-")
    assert stored(product.image)


def test_rejected_upload_shows_its_message_and_saves_nothing(
    client, staff_user, product
):
    client.force_login(staff_user)

    response = client.post(
        reverse("products:manage_product_update", kwargs={"pk": product.pk}),
        product_data(product, name="Renamed", image=image_upload(size=(400, 300))),
    )

    assert response.status_code == HTTPStatus.OK
    assert "800×1000 minimum" in response.content.decode()
    product.refresh_from_db()
    assert product.name == "Seraphine Home Hub"
    assert not product.image


def test_staff_can_remove_an_image(
    client, staff_user, product, django_capture_on_commit_callbacks
):
    name = give_image(product)
    client.force_login(staff_user)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse("products:manage_product_update", kwargs={"pk": product.pk}),
            product_data(product, **{"image-clear": "on"}),
        )

    product.refresh_from_db()
    assert not product.image
    assert not stored(name)


def test_editing_other_fields_keeps_the_image(client, staff_user, product):
    name = give_image(product)
    client.force_login(staff_user)

    client.post(
        reverse("products:manage_product_update", kwargs={"pk": product.pk}),
        product_data(product, price="299.99"),
    )

    product.refresh_from_db()
    assert product.image.name == name


def test_upload_and_remove_together_is_refused(client, staff_user, product):
    give_image(product)
    client.force_login(staff_user)

    response = client.post(
        reverse("products:manage_product_update", kwargs={"pk": product.pk}),
        product_data(product, image=image_upload(), **{"image-clear": "on"}),
    )

    assert "not both" in response.content.decode()


def test_edit_form_shows_the_current_image_and_remove_option(
    client, staff_user, product
):
    client.force_login(staff_user)
    url = reverse("products:manage_product_update", kwargs={"pk": product.pk})

    page = client.get(url).content.decode()
    assert 'enctype="multipart/form-data"' in page
    assert "placeholders/home-assistants.svg" in page
    assert "image-clear" not in page

    name = give_image(product)

    page = client.get(url).content.decode()
    assert f"/media/{name}" in page
    assert 'name="image-clear"' in page


def test_manage_list_shows_thumbnails(client, staff_user, product):
    name = give_image(product)
    client.force_login(staff_user)

    page = client.get(reverse("products:manage_products")).content.decode()

    assert f"/media/{name}" in page


def test_admin_uploads_are_processed_too(client, product):
    admin = get_user_model().objects.create_superuser(
        "root", email="root@example.com", password="root123"
    )
    client.force_login(admin)

    response = client.post(
        reverse("admin:products_product_change", args=[product.pk]),
        product_data(product, image=image_upload(size=(400, 300))),
    )

    assert "800×1000 minimum" in response.content.decode()
