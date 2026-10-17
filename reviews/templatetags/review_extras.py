from django import template

register = template.Library()


@register.filter
def changeable_by(review, user):
    """Whether ``user`` gets Edit and Delete on ``review`` — the model's
    ``can_be_changed_by``, callable from a template."""
    return review.can_be_changed_by(user)
