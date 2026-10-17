import re
from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from orders.models import Order, OrderItem

from .forms import ReviewForm
from .models import Review

SECTION = "reviews/partials/_reviews_section.html"
CARD = "reviews/partials/_review_card.html"
EDIT_FORM = "reviews/partials/_review_edit_form.html"
ALREADY_REVIEWED = (
    "You've already reviewed this product. You can edit your review below."
)
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


def test_the_author_can_change_their_review(customer, product):
    assert make_review(customer, product).can_be_changed_by(customer) is True


def test_other_customers_cannot_change_a_review(customer, other_customer, product):
    assert make_review(customer, product).can_be_changed_by(other_customer) is False


def test_signed_out_visitors_cannot_change_a_review(customer, product):
    assert make_review(customer, product).can_be_changed_by(AnonymousUser()) is False


def test_the_authors_edit_saves_without_the_staff_mark(customer, product):
    review = make_review(customer, product, rating=2)

    review.edit(customer, rating=4, comment="Grew on me.")

    review.refresh_from_db()
    assert (review.rating, review.comment, review.edited_by_staff) == (
        4,
        "Grew on me.",
        False,
    )


def test_staff_can_change_any_review(customer, staff_user, product):
    assert make_review(customer, product).can_be_changed_by(staff_user) is True


def test_a_staff_edit_of_someone_elses_review_marks_it(customer, staff_user, product):
    review = make_review(customer, product, rating=1, comment="Rude words.")

    review.edit(staff_user, rating=1, comment="Strong words.")

    review.refresh_from_db()
    assert review.comment == "Strong words."
    assert review.edited_by_staff is True


def test_a_staff_edit_of_their_own_review_is_not_marked(staff_user, product):
    review = make_review(staff_user, product, rating=3)

    review.edit(staff_user, rating=4, comment="Bought it myself.")

    review.refresh_from_db()
    assert review.edited_by_staff is False


def test_the_authors_later_edit_keeps_the_staff_mark(customer, staff_user, product):
    review = make_review(customer, product)
    review.edit(staff_user, rating=2, comment="Moderated.")

    review.edit(customer, rating=5, comment="My words again.")

    review.refresh_from_db()
    assert review.comment == "My words again."
    assert review.edited_by_staff is True


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


# --- Edit, cancel, update, delete -------------------------------------------


CHANGE_ENDPOINTS = [
    ("reviews:edit", "get"),
    ("reviews:cancel", "get"),
    ("reviews:update", "post"),
    ("reviews:delete", "post"),
]


@pytest.mark.parametrize(("name", "method"), CHANGE_ENDPOINTS)
def test_another_customers_review_is_a_404_and_unchanged(
    client, customer, other_customer, product, name, method
):
    review = make_review(other_customer, product, rating=4, comment="Mine, not yours.")
    client.force_login(customer)

    send = getattr(client, method)
    response = send(
        reverse(name, args=[review.pk]), {"rating": 1, "comment": "Tampered."}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    review.refresh_from_db()
    assert (review.rating, review.comment) == (4, "Mine, not yours.")


def test_a_valid_save_updates_the_review_and_returns_the_section(
    client, customer, other_customer, product
):
    make_order(customer, product)
    review = make_review(customer, product, rating=5, comment="Loves me back.")
    make_review(other_customer, product, rating=3, comment="Decent hub.")
    client.force_login(customer)

    response = client.post(
        reverse("reviews:update", args=[review.pk]),
        {"rating": 1, "comment": "  She stopped listening.  "},
    )

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == SECTION
    review.refresh_from_db()
    assert (review.rating, review.comment) == (1, "She stopped listening.")
    assert review.edited_by_staff is False
    assert "2.0 out of 5" in response.text
    assert "She stopped listening." in response.text
    assert "Loves me back." not in response.text


def test_deleting_your_review_brings_the_create_form_back(
    client, customer, other_customer, product
):
    make_order(customer, product)
    review = make_review(customer, product, rating=5, comment="Changed my mind.")
    make_review(other_customer, product, rating=3, comment="Decent hub.")
    client.force_login(customer)

    response = client.post(reverse("reviews:delete", args=[review.pk]))

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == SECTION
    assert not Review.objects.filter(pk=review.pk).exists()
    assert "Changed my mind." not in response.text
    assert response.context["section"].own is None
    assert reverse("reviews:create", args=[product.pk]) in response.text
    assert "3.0 out of 5" in response.text
    assert "1 review<" in response.text


def test_after_a_delete_the_customer_can_write_a_new_review(client, customer, product):
    make_order(customer, product)
    review = make_review(customer, product, comment="First try.")
    client.force_login(customer)
    client.post(reverse("reviews:delete", args=[review.pk]))

    response = create(client, product, {"rating": 4, "comment": "Second try."})

    assert response.status_code == HTTPStatus.OK
    assert Review.objects.get(user=customer).comment == "Second try."


def test_edit_returns_the_form_for_that_card(client, customer, product):
    review = make_review(customer, product, rating=3, comment="Pretty good.")
    client.force_login(customer)

    response = client.get(reverse("reviews:edit", args=[review.pk]))

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == EDIT_FORM
    assert f'id="review-{review.pk}"' in response.text
    assert reverse("reviews:update", args=[review.pk]) in response.text
    assert reverse("reviews:cancel", args=[review.pk]) in response.text
    assert "Pretty good." in response.text
    assert re.search(r'value="3"[^>]*\bchecked\b', response.text)


def test_cancel_returns_the_card_unchanged(client, customer, product):
    review = make_review(customer, product, rating=3, comment="Pretty good.")
    client.force_login(customer)

    response = client.get(reverse("reviews:cancel", args=[review.pk]))

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == CARD
    assert f'id="review-{review.pk}"' in response.text
    assert "Pretty good." in response.text
    assert reverse("reviews:edit", args=[review.pk]) in response.text


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"rating": 2, "comment": "   "}, "Write a few words about the product."),
        ({"comment": "Lost the stars."}, "Pick a star rating."),
        ({"rating": 2, "comment": "x" * 2001}, "at most 2000 characters"),
    ],
)
def test_an_invalid_save_re_renders_the_edit_form_and_changes_nothing(
    client, customer, product, data, error
):
    review = make_review(customer, product, rating=5, comment="Original words.")
    client.force_login(customer)

    response = client.post(reverse("reviews:update", args=[review.pk]), data)

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == EDIT_FORM
    assert error in response.text
    # The form posts to the section; the errors go back into the card.
    assert response.headers["HX-Retarget"] == f"#review-{review.pk}"
    assert response.headers["HX-Reswap"] == "outerHTML"
    review.refresh_from_db()
    assert (review.rating, review.comment) == (5, "Original words.")


def test_an_invalid_save_keeps_the_typed_input(client, customer, product):
    review = make_review(customer, product, rating=5, comment="Original words.")
    client.force_login(customer)

    response = client.post(
        reverse("reviews:update", args=[review.pk]),
        {"rating": 2, "comment": "x" * 2001},
    )

    assert "x" * 2001 in response.text
    assert re.search(r'value="2"[^>]*\bchecked\b', response.text)
    assert response.text.count("checked") == 1
    assert "Original words." not in response.text


@pytest.mark.parametrize("name", ["reviews:update", "reviews:delete"])
def test_update_and_delete_refuse_get(client, customer, product, name):
    review = make_review(customer, product)
    client.force_login(customer)

    response = client.get(reverse(name, args=[review.pk]))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert Review.objects.filter(pk=review.pk).exists()


@pytest.mark.parametrize(("name", "method"), CHANGE_ENDPOINTS)
def test_a_missing_review_is_a_404(client, customer, name, method):
    client.force_login(customer)

    response = getattr(client, method)(reverse(name, args=[999999]))

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(("name", "method"), CHANGE_ENDPOINTS)
def test_signed_out_requests_to_change_a_review_go_to_login(
    client, customer, product, name, method
):
    review = make_review(customer, product, rating=4, comment="Untouchable.")
    url = reverse(name, args=[review.pk])
    data = {"rating": 1, "comment": "Sneaky."} if method == "post" else {}

    response = getattr(client, method)(url, data)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"
    review.refresh_from_db()
    assert (review.rating, review.comment) == (4, "Untouchable.")


@pytest.mark.parametrize(("name", "method"), CHANGE_ENDPOINTS)
def test_signed_out_htmx_requests_to_change_a_review_get_hx_redirect(
    client, customer, product, name, method
):
    review = make_review(customer, product, rating=4, comment="Untouchable.")
    page = product.get_absolute_url()

    response = getattr(client, method)(
        reverse(name, args=[review.pk]),
        {"rating": 1, "comment": "Sneaky."},
        headers={"HX-Request": "true", "HX-Current-URL": f"http://testserver{page}"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers.get("HX-Redirect") == (
        f"{reverse('accounts:login')}?next={page}"
    )
    review.refresh_from_db()
    assert (review.rating, review.comment) == (4, "Untouchable.")


def test_after_a_cancellation_the_author_can_still_edit(client, customer, product):
    order = make_order(customer, product)
    review = make_review(customer, product, rating=5, comment="Before.")
    order.status = Order.Status.CANCELLED
    order.save()
    client.force_login(customer)

    edit = client.get(reverse("reviews:edit", args=[review.pk]))
    save = client.post(
        reverse("reviews:update", args=[review.pk]),
        {"rating": 2, "comment": "After."},
    )

    assert edit.status_code == save.status_code == HTTPStatus.OK
    review.refresh_from_db()
    assert (review.rating, review.comment) == (2, "After.")


def test_after_a_cancellation_the_author_can_still_delete(client, customer, product):
    order = make_order(customer, product)
    review = make_review(customer, product)
    order.status = Order.Status.CANCELLED
    order.save()
    client.force_login(customer)

    response = client.post(reverse("reviews:delete", args=[review.pk]))

    assert response.status_code == HTTPStatus.OK
    assert not Review.objects.exists()
    # Eligibility is checked again for a new review, and it's gone.
    assert NOT_ELIGIBLE in response.text


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


def test_the_author_gets_edit_and_delete_on_their_pinned_review_only(
    client, customer, other_customer, product
):
    mine = make_review(customer, product, comment="Mine.")
    theirs = make_review(other_customer, product, comment="Theirs.")
    client.force_login(customer)

    text = page(client, product).text

    assert reverse("reviews:edit", args=[mine.pk]) in text
    assert reverse("reviews:delete", args=[mine.pk]) in text
    assert reverse("reviews:edit", args=[theirs.pk]) not in text
    assert reverse("reviews:delete", args=[theirs.pk]) not in text


def test_delete_asks_for_confirmation(client, customer, product):
    make_review(customer, product)
    client.force_login(customer)

    assert "hx-confirm=" in page(client, product).text


def test_signed_out_visitors_get_no_edit_or_delete(client, customer, product):
    review = make_review(customer, product)

    text = page(client, product).text

    assert reverse("reviews:edit", args=[review.pk]) not in text
    assert reverse("reviews:delete", args=[review.pk]) not in text


# --- Staff moderation -------------------------------------------------------


def test_staff_get_edit_and_delete_on_every_review(
    client, customer, other_customer, staff_user, product
):
    reviews = [make_review(customer, product), make_review(other_customer, product)]
    client.force_login(staff_user)

    text = page(client, product).text

    for review in reviews:
        assert reverse("reviews:edit", args=[review.pk]) in text
        assert reverse("reviews:delete", args=[review.pk]) in text


@pytest.mark.parametrize("name", ["reviews:edit", "reviews:cancel"])
def test_staff_can_open_and_cancel_an_edit_on_any_review(
    client, customer, staff_user, product, name
):
    review = make_review(customer, product, comment="Customer words.")
    client.force_login(staff_user)

    response = client.get(reverse(name, args=[review.pk]))

    assert response.status_code == HTTPStatus.OK
    assert "Customer words." in response.text


def test_a_staff_save_on_a_customers_review_shows_the_badge(
    client, customer, staff_user, product
):
    review = make_review(customer, product, rating=1, comment="Rude words.")
    client.force_login(staff_user)

    response = client.post(
        reverse("reviews:update", args=[review.pk]),
        {"rating": 1, "comment": "Strong words."},
    )

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == SECTION
    review.refresh_from_db()
    assert (review.user, review.comment, review.edited_by_staff) == (
        customer,
        "Strong words.",
        True,
    )
    assert "Edited by staff" in response.text


def test_staff_can_delete_any_review(client, customer, staff_user, product):
    review = make_review(customer, product, comment="Off-topic.")
    client.force_login(staff_user)

    response = client.post(reverse("reviews:delete", args=[review.pk]))

    assert response.status_code == HTTPStatus.OK
    assert [t.name for t in response.templates][0] == SECTION
    assert not Review.objects.exists()
    assert EMPTY_STATE in response.text


def test_staff_without_a_purchase_get_the_note_and_a_403(client, staff_user, product):
    client.force_login(staff_user)

    note = page(client, product)
    response = create(client, product, {"rating": 5, "comment": "Staff pick."})

    assert NOT_ELIGIBLE in note.text
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert not Review.objects.exists()


def test_staff_with_a_purchase_can_review(client, staff_user, product):
    make_order(staff_user, product)
    client.force_login(staff_user)

    response = create(client, product, {"rating": 5, "comment": "Bought my own."})

    assert response.status_code == HTTPStatus.OK
    review = Review.objects.get(user=staff_user)
    assert review.edited_by_staff is False


# --- Django admin -----------------------------------------------------------


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="overseer", email="overseer@example.com", password="overseer123"
    )


def test_the_admin_changelist_filters_and_searches(
    client, superuser, customer, other_customer, product
):
    make_review(customer, product, rating=5)
    make_review(other_customer, product, rating=2)
    client.force_login(superuser)
    url = reverse("admin:reviews_review_changelist")

    everything = client.get(url)
    two_stars = client.get(url, {"rating__exact": 2})
    by_user = client.get(url, {"q": "jordan"})
    by_product = client.get(url, {"q": "Seraphine"})

    assert everything.status_code == HTTPStatus.OK
    assert everything.context["cl"].result_count == 2
    assert [r.user for r in two_stars.context["cl"].result_list] == [other_customer]
    assert [r.user for r in by_user.context["cl"].result_list] == [other_customer]
    assert by_product.context["cl"].result_count == 2


def test_the_admin_refuses_to_add_a_review(client, superuser):
    client.force_login(superuser)

    response = client.get(reverse("admin:reviews_review_add"))

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_the_admin_refuses_to_change_a_review(client, superuser, customer, product):
    review = make_review(customer, product, rating=4, comment="Original.")
    client.force_login(superuser)

    response = client.post(
        reverse("admin:reviews_review_change", args=[review.pk]),
        {
            "user": customer.pk,
            "product": product.pk,
            "rating": 1,
            "comment": "Rewritten.",
            "edited_by_staff": "",
            "created_at_0": "2026-01-01",
            "created_at_1": "00:00:00",
        },
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    review.refresh_from_db()
    assert (review.rating, review.comment) == (4, "Original.")


def test_the_admin_can_delete_a_review(client, superuser, customer, product):
    review = make_review(customer, product)
    client.force_login(superuser)

    response = client.post(
        reverse("admin:reviews_review_delete", args=[review.pk]), {"post": "yes"}
    )

    assert response.status_code == HTTPStatus.FOUND
    assert not Review.objects.exists()
