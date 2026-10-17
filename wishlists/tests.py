from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from products.models import Product

from .models import Wishlist, WishlistItem

BUTTON = "wishlists/partials/_wishlist_button.html"


@pytest.fixture
def wishlist(customer):
    return Wishlist.for_user(customer)


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(
        username="other", email="other@example.com", password="other123"
    )


# --- Model behavior ---------------------------------------------------------


def test_wishlist_str(wishlist):
    assert str(wishlist) == "Wishlist for customer"


def test_for_user_creates_the_wishlist_once(customer):
    first = Wishlist.for_user(customer)
    second = Wishlist.for_user(customer)

    assert first == second
    assert Wishlist.objects.count() == 1


def test_add_saves_the_product(wishlist, product):
    item = wishlist.add(product)

    assert str(item) == "Seraphine Home Hub"
    assert wishlist.has(product)


def test_adding_twice_leaves_one_item(wishlist, product):
    wishlist.add(product)
    wishlist.add(product)

    assert wishlist.items.count() == 1


def test_wishlist_product_pair_is_unique(wishlist, product):
    wishlist.add(product)

    with pytest.raises(IntegrityError):
        WishlistItem.objects.create(wishlist=wishlist, product=product)


def test_remove_drops_the_product(wishlist, product):
    wishlist.add(product)

    wishlist.remove(product)

    assert not wishlist.has(product)


def test_removing_an_unsaved_product_does_nothing(wishlist, product, category):
    wishlist.add(product)
    other = Product.objects.create(
        name="Charging Pillow",
        slug="charging-pillow",
        price=Decimal("69.00"),
        category=category,
    )

    wishlist.remove(other)

    assert list(wishlist.items.values_list("product", flat=True)) == [product.pk]


def test_has_is_per_wishlist(wishlist, product, other_customer):
    Wishlist.for_user(other_customer).add(product)

    assert not wishlist.has(product)


def test_deleting_a_product_deletes_its_wishlist_items(wishlist, product):
    wishlist.add(product)

    product.delete()

    assert not WishlistItem.objects.exists()


# --- Add and remove endpoints ----------------------------------------------


@pytest.mark.parametrize("name", ["wishlists:add", "wishlists:remove"])
def test_signed_out_posts_go_to_login(client, product, name):
    url = reverse(name, args=[product.pk])

    response = client.post(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"
    assert not WishlistItem.objects.exists()


@pytest.mark.parametrize("name", ["wishlists:add", "wishlists:remove"])
def test_get_is_not_allowed(client, customer, product, name):
    client.force_login(customer)

    response = client.get(reverse(name, args=[product.pk]))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_add_saves_and_renders_the_saved_button(client, customer, product):
    client.force_login(customer)

    response = client.post(reverse("wishlists:add", args=[product.pk]))

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates] == [BUTTON]
    assert b"<html" not in response.content
    assert "Saved ✓ — Remove" in response.text
    assert reverse("wishlists:remove", args=[product.pk]) in response.text
    assert Wishlist.for_user(customer).has(product)


def test_adding_twice_through_the_endpoint_leaves_one_item(client, customer, product):
    client.force_login(customer)
    url = reverse("wishlists:add", args=[product.pk])

    client.post(url)
    response = client.post(url)

    assert response.status_code == HTTPStatus.OK
    assert WishlistItem.objects.count() == 1


def test_an_unavailable_product_can_be_added(client, customer, unavailable_product):
    client.force_login(customer)

    response = client.post(reverse("wishlists:add", args=[unavailable_product.pk]))

    assert response.status_code == HTTPStatus.OK
    assert Wishlist.for_user(customer).has(unavailable_product)


def test_remove_unsaves_and_renders_the_save_button(client, customer, product):
    Wishlist.for_user(customer).add(product)
    client.force_login(customer)

    response = client.post(reverse("wishlists:remove", args=[product.pk]))

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates] == [BUTTON]
    assert b"<html" not in response.content
    assert "Save to wishlist" in response.text
    assert reverse("wishlists:add", args=[product.pk]) in response.text
    assert not Wishlist.for_user(customer).has(product)


def test_removing_an_unsaved_product_succeeds_and_changes_nothing(
    client, customer, product, unavailable_product
):
    Wishlist.for_user(customer).add(unavailable_product)
    client.force_login(customer)

    response = client.post(reverse("wishlists:remove", args=[product.pk]))

    assert response.status_code == HTTPStatus.OK
    assert "Save to wishlist" in response.text
    assert list(WishlistItem.objects.values_list("product", flat=True)) == [
        unavailable_product.pk
    ]


@pytest.mark.parametrize("name", ["wishlists:add", "wishlists:remove"])
def test_a_nonexistent_product_is_a_404(client, customer, name):
    client.force_login(customer)

    response = client.post(reverse(name, args=[999999]))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_and_remove_touch_only_the_requesters_wishlist(
    client, customer, other_customer, product
):
    Wishlist.for_user(other_customer).add(product)
    client.force_login(customer)

    client.post(reverse("wishlists:add", args=[product.pk]))
    client.post(reverse("wishlists:remove", args=[product.pk]))

    assert Wishlist.for_user(other_customer).has(product)
    assert not Wishlist.for_user(customer).has(product)


def test_staff_have_their_own_wishlist(client, staff_user, customer, product):
    client.force_login(staff_user)

    response = client.post(reverse("wishlists:add", args=[product.pk]))

    assert response.status_code == HTTPStatus.OK
    assert Wishlist.for_user(staff_user).has(product)
    assert not Wishlist.for_user(customer).has(product)


# --- The button on the product page ----------------------------------------


def test_signed_out_detail_page_links_to_login(client, product):
    response = client.get(product.get_absolute_url())

    login = f"{reverse('accounts:login')}?next={product.get_absolute_url()}"
    assert f'href="{login}"' in response.text
    assert reverse("wishlists:add", args=[product.pk]) not in response.text
    assert not Wishlist.objects.exists()


def test_signing_in_from_the_link_returns_to_the_product(client, customer, product):
    response = client.post(
        reverse("accounts:login"),
        {
            "username": "customer",
            "password": "customer123",
            "next": product.get_absolute_url(),
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == product.get_absolute_url()


def test_detail_page_offers_save_when_not_saved(client, customer, product):
    client.force_login(customer)

    response = client.get(product.get_absolute_url())

    assert response.context["on_wishlist"] is False
    assert reverse("wishlists:add", args=[product.pk]) in response.text
    assert "Save to wishlist" in response.text
    assert not Wishlist.objects.exists()


def test_detail_page_shows_saved_when_saved(client, customer, product):
    Wishlist.for_user(customer).add(product)
    client.force_login(customer)

    response = client.get(product.get_absolute_url())

    assert response.context["on_wishlist"] is True
    assert reverse("wishlists:remove", args=[product.pk]) in response.text
    assert "Saved ✓ — Remove" in response.text


def test_detail_page_ignores_other_users_wishlists(
    client, customer, other_customer, product
):
    Wishlist.for_user(other_customer).add(product)
    client.force_login(customer)

    response = client.get(product.get_absolute_url())

    assert response.context["on_wishlist"] is False


def test_unavailable_detail_page_still_offers_save(
    client, customer, unavailable_product
):
    client.force_login(customer)

    response = client.get(unavailable_product.get_absolute_url())

    assert reverse("wishlists:add", args=[unavailable_product.pk]) in response.text


# --- The My wishlist page ---------------------------------------------------


def make_product(category, name, slug):
    return Product.objects.create(
        name=name, slug=slug, price=Decimal("10.00"), category=category
    )


@pytest.mark.parametrize("requester", ["customer", "staff_user"])
def test_page_lists_only_the_requesters_items_newest_first(
    request, client, customer, staff_user, product, category, requester
):
    user = request.getfixturevalue(requester)
    other_user = staff_user if user == customer else customer
    older = make_product(category, "Thought Mug", "thought-mug")
    newer = make_product(category, "Mind Lamp", "mind-lamp")
    wishlist = Wishlist.for_user(user)
    # Created so pk order disagrees with added_at: only added_at puts the
    # newer item first.
    WishlistItem.objects.create(
        wishlist=wishlist, product=newer, added_at=timezone.now()
    )
    WishlistItem.objects.create(
        wishlist=wishlist,
        product=older,
        added_at=timezone.now() - timedelta(days=2),
    )
    Wishlist.for_user(other_user).add(product)
    client.force_login(user)

    response = client.get(reverse("wishlists:detail"))

    assert response.status_code == HTTPStatus.OK
    text = response.text
    assert "Mind Lamp" in text and "Thought Mug" in text
    assert text.index("Mind Lamp") < text.index("Thought Mug")
    assert newer.get_absolute_url() in text
    assert newer.image_url in text
    assert "$10.00" in text
    assert product.name not in text


def test_page_badges_an_unavailable_product(
    client, customer, product, unavailable_product
):
    wishlist = Wishlist.for_user(customer)
    wishlist.add(product)
    wishlist.add(unavailable_product)
    client.force_login(customer)

    response = client.get(reverse("wishlists:detail"))

    badge = '<span class="badge badge-warning badge-outline">Unavailable</span>'
    assert unavailable_product.name in response.text
    assert badge in response.text
    # Only the unavailable product is badged, not the available one.
    assert response.text.count("Unavailable") == 1


CONTENTS = "wishlists/partials/_wishlist_contents.html"


def test_navbar_shows_wishlist_to_signed_in_users_only(client, customer):
    link = f'href="{reverse("wishlists:detail")}"'

    assert link not in client.get(reverse("products:catalog")).text

    client.force_login(customer)
    assert link in client.get(reverse("products:catalog")).text


def test_signed_out_page_goes_to_login(client):
    url = reverse("wishlists:detail")

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_signed_out_remove_item_goes_to_login(client, wishlist, product):
    item = wishlist.add(product)
    url = reverse("wishlists:remove_item", args=[item.pk])

    response = client.post(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"
    assert WishlistItem.objects.filter(pk=item.pk).exists()


def test_remove_item_get_is_not_allowed(client, customer, wishlist, product):
    item = wishlist.add(product)
    client.force_login(customer)

    response = client.get(reverse("wishlists:remove_item", args=[item.pk]))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_empty_wishlist_shows_the_empty_state(client, customer):
    client.force_login(customer)

    response = client.get(reverse("wishlists:detail"))

    assert "Your wishlist is empty" in response.text
    assert reverse("products:catalog") in response.text


def test_page_has_a_remove_button_per_item(client, customer, wishlist, product):
    item = wishlist.add(product)
    client.force_login(customer)

    response = client.get(reverse("wishlists:detail"))

    assert reverse("wishlists:remove_item", args=[item.pk]) in response.text
    assert 'hx-target="#wishlist-contents"' in response.text
    assert "Your wishlist is empty" not in response.text


def test_remove_item_deletes_and_renders_the_contents_alone(
    client, customer, wishlist, product, unavailable_product
):
    item = wishlist.add(product)
    wishlist.add(unavailable_product)
    client.force_login(customer)

    response = client.post(reverse("wishlists:remove_item", args=[item.pk]))

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates] == [CONTENTS]
    assert b"<html" not in response.content
    assert product.name not in response.text
    assert unavailable_product.name in response.text
    assert not wishlist.has(product)


def test_removing_the_last_item_shows_the_empty_state(
    client, customer, wishlist, product
):
    item = wishlist.add(product)
    client.force_login(customer)

    response = client.post(reverse("wishlists:remove_item", args=[item.pk]))

    assert "Your wishlist is empty" in response.text
    assert not WishlistItem.objects.exists()


def test_remove_item_on_another_users_item_is_a_404(
    client, customer, other_customer, product
):
    theirs = Wishlist.for_user(other_customer).add(product)
    client.force_login(customer)

    response = client.post(reverse("wishlists:remove_item", args=[theirs.pk]))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert WishlistItem.objects.filter(pk=theirs.pk).exists()


def test_staff_cannot_remove_a_customers_item(client, staff_user, wishlist, product):
    item = wishlist.add(product)
    client.force_login(staff_user)

    response = client.post(reverse("wishlists:remove_item", args=[item.pk]))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert WishlistItem.objects.filter(pk=item.pk).exists()


def test_a_deleted_product_drops_off_the_page(client, customer, wishlist, product):
    wishlist.add(product)
    product.delete()
    client.force_login(customer)

    response = client.get(reverse("wishlists:detail"))

    assert "Seraphine Home Hub" not in response.text
    assert "Your wishlist is empty" in response.text


# --- The seeded demo wishlist ----------------------------------------------


def seeded_wishlist():
    """Every seeded wishlist item, newest first, minus its run-relative time."""
    return list(
        WishlistItem.objects.values_list("wishlist__user__username", "product__slug")
    )


def test_seed_gives_customer_a_wishlist(db):
    call_command("seed")

    customer = get_user_model().objects.get(username="customer")
    items = list(customer.wishlist.lines())
    assert 3 <= len(items) <= 4
    assert WishlistItem.objects.exclude(wishlist__user=customer).count() == 0
    assert any(not item.product.is_available for item in items)

    added = [item.added_at for item in items]
    assert len(set(added)) == len(added)
    assert all(when < timezone.now() for when in added)


def test_seeding_twice_gives_the_same_wishlist(db):
    call_command("seed")
    first = seeded_wishlist()

    call_command("seed")

    assert seeded_wishlist() == first
