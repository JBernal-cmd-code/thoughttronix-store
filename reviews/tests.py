import re
from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from orders.models import Order, OrderItem

from .forms import ReviewForm
from .models import Review

SECTION = "reviews/partials/_reviews_section.html"
ALREADY_REVIEWED = "You've already reviewed this product."
NOT_ELIGIBLE = "Only customers who've purchased this product can review it."
SIGN_IN = "Sign in to write a review"
EMPTY_STATE = "No reviews yet"


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(
        username="jordan",
        email="jordan@example.com",
        password="jordan123",
        first_name="Jordan",
        last_name="Park",
    )


def make_review(user, product, rating=4, comment="Does what it says.", days_ago=0):
    return Review.objects.create(
        user=user,
        product=product,
        rating=rating,
        comment=comment,
        created_at=timezone.now() - timedelta(days=days_ago),
    )


def make_order(user, product, status=Order.Status.PLACED):
    """An order on ``user``'s account containing one ``product``."""
    order = Order.objects.create(
        user=user,
        status=status,
        total=product.price,
        email=user.email,
        shipping_name="Casey Monroe",
        shipping_street="9 Synapse Court",
        shipping_city="Canyon",
        shipping_state="TX",
        shipping_zip="79015",
        billing_name="Casey Monroe",
        billing_street="9 Synapse Court",
        billing_city="Canyon",
        billing_state="TX",
        billing_zip="79015",
        card_last4="4242",
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        unit_price=Decimal(product.price),
        quantity=1,
    )
    return order


# --- Eligibility ------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "eligible"),
    [
        (Order.Status.PLACED, True),
        (Order.Status.SHIPPED, True),
        (Order.Status.DELIVERED, True),
        (Order.Status.CANCELLED, False),
    ],
)
def test_eligibility_follows_the_order_status(customer, product, status, eligible):
    make_order(customer, product, status)

    assert Review.is_eligible(customer, product) is eligible


def test_no_order_means_not_eligible(customer, product):
    assert Review.is_eligible(customer, product) is False


def test_another_accounts_order_does_not_qualify(customer, other_customer, product):
    order = make_order(other_customer, product)
    # The names typed on an order give no one eligibility.
    order.shipping_name = order.billing_name = "Customer"
    order.save()

    assert Review.is_eligible(customer, product) is False


def test_an_unavailable_product_qualifies(customer, unavailable_product):
    make_order(customer, unavailable_product)

    assert Review.is_eligible(customer, unavailable_product) is True


def test_one_live_order_outweighs_a_cancelled_one(customer, product):
    make_order(customer, product, Order.Status.CANCELLED)
    make_order(customer, product, Order.Status.DELIVERED)

    assert Review.is_eligible(customer, product) is True


def test_a_later_cancellation_leaves_the_review(client, customer, product):
    order = make_order(customer, product)
    review = make_review(customer, product, comment="Still mine.")

    order.status = Order.Status.CANCELLED
    order.save()
    client.force_login(customer)
    response = client.get(product.get_absolute_url())

    assert Review.objects.filter(pk=review.pk).exists()
    assert response.context["reviews_section"].own == review
    assert "Still mine." in response.text


# --- Model ------------------------------------------------------------------


@pytest.mark.parametrize("rating", [1, 5])
def test_ratings_one_to_five_are_accepted(customer, product, rating):
    Review(user=customer, product=product, rating=rating, comment="Fine.").full_clean()


@pytest.mark.parametrize("rating", [0, 6])
def test_ratings_outside_one_to_five_are_refused(customer, product, rating):
    review = Review(user=customer, product=product, rating=rating, comment="Fine.")

    with pytest.raises(ValidationError) as error:
        review.full_clean()

    assert "rating" in error.value.message_dict


@pytest.mark.parametrize("comment", ["", "   ", "\n\t "])
def test_an_empty_or_blank_comment_is_refused(customer, product, comment):
    review = Review(user=customer, product=product, rating=3, comment=comment)

    with pytest.raises(ValidationError) as error:
        review.full_clean()

    assert "comment" in error.value.message_dict


def test_the_comment_holds_two_thousand_characters(customer, product):
    Review(user=customer, product=product, rating=3, comment="x" * 2000).full_clean()


def test_a_longer_comment_is_refused(customer, product):
    review = Review(user=customer, product=product, rating=3, comment="x" * 2001)

    with pytest.raises(ValidationError) as error:
        review.full_clean()

    assert "comment" in error.value.message_dict


def test_one_review_per_customer_per_product(customer, product):
    make_review(customer, product)

    with pytest.raises(IntegrityError):
        make_review(customer, product)


def test_reviews_come_newest_first(customer, other_customer, product):
    older = make_review(customer, product, days_ago=3)
    newer = make_review(other_customer, product, days_ago=1)

    assert list(Review.objects.all()) == [newer, older]


def test_author_name_is_first_name_and_last_initial(other_customer, product):
    assert make_review(other_customer, product).author_name == "Jordan P."


def test_author_name_without_a_last_name_is_the_first_name(customer, product):
    customer.first_name = "Casey"
    customer.save()

    assert make_review(customer, product).author_name == "Casey"


def test_author_name_falls_back_without_a_first_name(customer, product):
    customer.last_name = "Monroe"
    customer.save()

    assert make_review(customer, product).author_name == "Verified buyer"


def test_deleting_a_product_deletes_its_reviews(customer, product):
    make_review(customer, product)

    product.delete()

    assert not Review.objects.exists()


def test_deleting_a_user_deletes_their_reviews(customer, product):
    make_review(customer, product)

    customer.delete()

    assert not Review.objects.exists()


# --- Create -----------------------------------------------------------------


def create(client, product, data):
    return client.post(reverse("reviews:create", args=[product.pk]), data)


def test_a_valid_create_saves_and_returns_the_updated_section(
    client, customer, other_customer, product
):
    make_order(customer, product)
    make_review(other_customer, product, rating=3, comment="Decent hub.")
    client.force_login(customer)

    response = create(client, product, {"rating": 5, "comment": "  Loves me back.  "})

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == SECTION
    assert b"<html" not in response.content
    review = Review.objects.get(user=customer)
    assert (review.product, review.rating, review.comment) == (
        product,
        5,
        "Loves me back.",
    )
    assert "4.0 out of 5" in response.text
    assert "2 reviews" in response.text
    assert "Your review" in response.text
    assert reverse("reviews:create", args=[product.pk]) not in response.text


def test_an_invalid_create_keeps_the_typed_input(client, customer, product):
    make_order(customer, product)
    client.force_login(customer)

    response = create(client, product, {"comment": "Forgot the stars."})

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == SECTION
    assert "Pick a star rating." in response.text
    assert "Forgot the stars." in response.text
    assert not Review.objects.exists()


def test_a_blank_comment_is_refused_and_the_rating_kept(client, customer, product):
    make_order(customer, product)
    client.force_login(customer)

    response = create(client, product, {"rating": 4, "comment": "    "})

    assert "Write a few words about the product." in response.text
    assert re.search(r'value="4"[^>]*\bchecked\b', response.text)
    assert response.text.count("checked") == 1
    assert not Review.objects.exists()


def test_a_too_long_comment_is_refused(client, customer, product):
    make_order(customer, product)
    client.force_login(customer)

    response = create(client, product, {"rating": 4, "comment": "x" * 2001})

    assert "at most 2000 characters" in response.text
    assert not Review.objects.exists()


def test_an_ineligible_create_is_forbidden_and_creates_nothing(
    client, customer, product
):
    make_order(customer, product, Order.Status.CANCELLED)
    client.force_login(customer)

    response = create(client, product, {"rating": 5, "comment": "Never bought it."})

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert not Review.objects.exists()


def test_create_on_a_missing_product_is_a_404(client, customer):
    client.force_login(customer)

    response = client.post(reverse("reviews:create", args=[999999]))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_create_get_is_not_allowed(client, customer, product):
    client.force_login(customer)

    response = client.get(reverse("reviews:create", args=[product.pk]))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_a_second_create_shows_the_existing_review_and_creates_nothing(
    client, customer, product
):
    make_order(customer, product)
    Review.objects.create(
        user=customer, product=product, rating=4, comment="Listens beautifully."
    )
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", args=[product.pk]),
        {"rating": 1, "comment": "Posted again from a stale tab."},
    )

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == SECTION
    assert ALREADY_REVIEWED in response.text
    assert "Listens beautifully." in response.text
    assert "Posted again from a stale tab." not in response.text
    assert Review.objects.count() == 1


def test_a_simultaneous_duplicate_is_answered_the_same_way(
    client, customer, product, monkeypatch
):
    """A twin request's review lands between the view's check and its save;
    the unique constraint refuses the second, and the view recovers."""
    make_order(customer, product)
    original_is_valid = ReviewForm.is_valid

    def validate_then_twin_commits(form):
        valid = original_is_valid(form)
        Review.objects.create(
            user=customer, product=product, rating=5, comment="The twin got here."
        )
        return valid

    monkeypatch.setattr(ReviewForm, "is_valid", validate_then_twin_commits)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", args=[product.pk]),
        {"rating": 2, "comment": "The slower request."},
    )

    assert response.status_code == HTTPStatus.OK
    assert ALREADY_REVIEWED in response.text
    assert "The twin got here." in response.text
    assert list(Review.objects.values_list("comment", flat=True)) == [
        "The twin got here."
    ]


# --- Access -----------------------------------------------------------------


def test_a_signed_out_htmx_create_redirects_the_whole_page_to_login(client, product):
    """HTMX would swap a plain 302's login page into the section; instead the
    browser is told to navigate, returning to the product after sign-in."""
    page = product.get_absolute_url()

    response = client.post(
        reverse("reviews:create", args=[product.pk]),
        {"rating": 5, "comment": "Sneaky."},
        headers={"HX-Request": "true", "HX-Current-URL": f"http://testserver{page}"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers.get("HX-Redirect") == (
        f"{reverse('accounts:login')}?next={page}"
    )
    assert not Review.objects.exists()


def test_a_signed_out_plain_create_goes_to_login(client, product):
    url = reverse("reviews:create", args=[product.pk])

    response = client.post(url, {"rating": 5, "comment": "Sneaky."})

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"
    assert not Review.objects.exists()


def test_hx_redirect_keeps_only_the_path_of_the_current_url(client, product):
    response = client.post(
        reverse("reviews:create", args=[product.pk]),
        headers={
            "HX-Request": "true",
            "HX-Current-URL": "https://evil.example/products/x/?page=2",
        },
    )

    assert response.headers["HX-Redirect"] == (
        f"{reverse('accounts:login')}?next=/products/x/%3Fpage%3D2"
    )


# --- The section on the product page ----------------------------------------


def page(client, product):
    return client.get(product.get_absolute_url())


def test_signed_out_visitors_get_a_sign_in_link(client, product):
    response = page(client, product)

    login = f"{reverse('accounts:login')}?next={product.get_absolute_url()}"
    assert SIGN_IN in response.text
    assert f'href="{login}"' in response.text
    assert reverse("reviews:create", args=[product.pk]) not in response.text


def test_signing_in_from_the_link_returns_to_the_product(client, customer, product):
    response = client.post(
        reverse("accounts:login"),
        {
            "username": "customer",
            "password": "customer123",
            "next": product.get_absolute_url(),
        },
    )

    assert response.url == product.get_absolute_url()


def test_customers_who_have_not_bought_it_get_the_note(client, customer, product):
    client.force_login(customer)

    response = page(client, product)

    assert NOT_ELIGIBLE in response.text
    assert SIGN_IN not in response.text
    assert reverse("reviews:create", args=[product.pk]) not in response.text


def test_eligible_customers_get_the_form(client, customer, product):
    make_order(customer, product)
    client.force_login(customer)

    response = page(client, product)

    assert reverse("reviews:create", args=[product.pk]) in response.text
    assert 'hx-target="#reviews"' in response.text
    assert NOT_ELIGIBLE not in response.text


def test_a_reviewer_sees_their_review_pinned_instead_of_the_form(
    client, customer, product
):
    make_order(customer, product)
    make_review(customer, product, comment="My own words.")
    client.force_login(customer)

    response = page(client, product)

    assert "Your review" in response.text
    assert "My own words." in response.text
    assert response.text.count("My own words.") == 1
    assert reverse("reviews:create", args=[product.pk]) not in response.text


def test_others_reviews_list_newest_first_without_the_requesters_own(
    client, customer, other_customer, staff_user, product
):
    make_order(customer, product)
    make_review(other_customer, product, comment="Older thoughts.", days_ago=5)
    make_review(customer, product, comment="Mine.", days_ago=3)
    make_review(staff_user, product, comment="Newer thoughts.", days_ago=1)
    client.force_login(customer)

    section = page(client, product).context["reviews_section"]

    assert [r.comment for r in section.others] == [
        "Newer thoughts.",
        "Older thoughts.",
    ]
    assert section.own.comment == "Mine."


def test_signed_out_visitors_see_every_review(
    client, customer, other_customer, product
):
    make_review(customer, product, comment="First.", days_ago=2)
    make_review(other_customer, product, comment="Second.", days_ago=1)

    text = page(client, product).text

    assert text.index("Second.") < text.index("First.")


def test_the_summary_shows_the_average_and_count(
    client, customer, other_customer, product
):
    make_review(customer, product, rating=5)
    make_review(other_customer, product, rating=2)

    response = page(client, product)

    assert "3.5 out of 5" in response.text
    assert "2 reviews" in response.text
    assert EMPTY_STATE not in response.text


def test_a_single_review_is_counted_singular(client, customer, product):
    make_review(customer, product, rating=4)

    assert "1 review<" in page(client, product).text


def test_an_unreviewed_product_shows_the_empty_state(client, product):
    response = page(client, product)

    assert EMPTY_STATE in response.text
    assert "out of 5" not in response.text


def test_cards_show_the_author_name_never_the_username(client, other_customer, product):
    make_review(other_customer, product)

    text = page(client, product).text

    assert "Jordan P." in text
    assert "jordan@example.com" not in text
    assert ">jordan<" not in text


def test_a_staff_edited_review_is_badged(client, customer, other_customer, product):
    edited = make_review(customer, product, comment="Tidied up.")
    edited.edited_by_staff = True
    edited.save()
    make_review(other_customer, product, comment="Untouched.")

    response = page(client, product)

    assert response.text.count("Edited by staff") == 1
