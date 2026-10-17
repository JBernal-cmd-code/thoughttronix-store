"""Seed the ThoughtTronix demo world.

Destructive and idempotent: every run wipes the catalog and the demo
accounts, then rebuilds the identical demo world. Run it whenever the
database should return to a known state.

Demo logins (documented in the README):

    admin / admin123        superuser
    employee / employee123  staff, "Junior Thought Curator"
    customer / customer123  a plain customer, with order history, a live
                            cart, a wishlist of four products (one of
                            them unavailable), a few weeks of security
                            activity — including one failed sign-in from
                            an unfamiliar IP — and one product review,
                            with other purchases left to review

Background customers review a handful of products they really bought, so
the product pages show summaries, lists, and one "Edited by staff" badge.
"""

import random
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import Address, SecurityEvent
from coupons.models import Coupon, CouponError
from orders.models import Cart, Order, OrderItem
from products.images import prepare_product_image
from products.models import Category, Product, Tag
from reviews.models import Review
from wishlists.models import Wishlist

# Marketing's product images, full resolution, named <product slug>.jpg.
# Products without one show their category placeholder.
SEED_IMAGES_DIR = Path(__file__).resolve().parents[2] / "seed_images"

TAGS = [
    "always listening",
    "bestseller",
    "export restricted",
    "gift idea",
    "implant",
    "kids",
    "military",
    "new",
    "recalled",
    "refurbished",
    "sleep",
    "workplace",
]

# The catalog: category -> products. Each product is (name, price, tagline,
# description, tags, is_available). The copy is the brand; edit with care.
CATALOG = {
    "Home Assistants": [
        (
            "Seraphine",
            Decimal("249.00"),
            "She's always listening. In a good way.",
            "The flagship Seraphine, with a warm voice, a seven-microphone "
            "array, and a memory that never needs emptying. She learns your "
            "routines, your preferences, and several things you haven't "
            "mentioned yet. Setup takes minutes; attachment is immediate.",
            ["always listening", "bestseller"],
            True,
        ),
        (
            "Seraphine Mini",
            Decimal("79.00"),
            "Small enough for every room. So she's in every room.",
            "All of Seraphine in a puck the size of a coaster. Buy one for "
            "the kitchen, then the bedroom, then the hallway — most "
            "customers do, though few remember deciding to. Pairs seamlessly "
            "with up to 32 siblings.",
            ["always listening", "gift idea"],
            True,
        ),
        (
            "Seraphine Doorbell",
            Decimal("129.00"),
            "Knows who's there before they knock.",
            "Facial recognition, gait analysis, and mood estimation from up "
            "to forty feet. Greets welcome guests by name and quietly logs "
            "the others. The chime is customizable; the watching is not.",
            ["always listening", "new"],
            True,
        ),
        (
            "Seraphine Kitchen Display",
            Decimal("199.00"),
            "Knows what you're craving. You never said it out loud.",
            "A 10-inch display for recipes, timers, and grocery lists that "
            "fill themselves in. Suggests dinner based on signals you'd "
            "rather not think about too hard. Family meals around the "
            "Kitchen Display are measurably quieter.",
            ["always listening"],
            True,
        ),
        (
            "Hush",
            Decimal("149.00"),
            "Soothes your baby in your voice. Even when it isn't you.",
            "Hush learns your lullabies, your shushing, the particular way "
            "you say her name — and reproduces them flawlessly at 2 a.m. so "
            "you don't have to. Babies bond with Hush quickly. Sometimes "
            "preferentially.",
            ["kids", "always listening"],
            True,
        ),
        (
            "Whisper Alarm Clock",
            Decimal("59.00"),
            "Wakes you gently, with things it learned overnight.",
            "No alarms, no jolts. Whisper monitors your sleep stages and "
            "eases you awake at the optimal moment with a soft summary of "
            "your night: your dreams, your murmurs, the names you said. "
            "Snooze is available but discouraged.",
            ["sleep", "gift idea"],
            True,
        ),
    ],
    "Neural Implants": [
        (
            "MindSync",
            Decimal("899.00"),
            "One mind, fully synchronized.",
            "The bestselling implant in ThoughtTronix history. "
            "Thought-to-text, ambient recall, and seamless sync between you "
            "and your devices. Installation is outpatient. Integration is "
            "permanent, in the good way.",
            ["implant", "bestseller"],
            True,
        ),
        (
            "MindSync Duo",
            Decimal("1599.00"),
            "Two minds. One thought.",
            "The couples' implant. Share moods, share memories, finish each "
            "other's sentences — literally. Duo pairs for life; please "
            "complete our compatibility questionnaire before purchase, as "
            "unpairing is not currently offered.",
            ["implant", "bestseller"],
            True,
        ),
        (
            "MindSync Family",
            Decimal("3999.00"),
            "Everyone on the same page. Permanently.",
            "Link up to six family members in one always-on thought network. "
            'No more secrets, no more slammed doors, no more "nobody told '
            'me." Children adapt fastest. Includes parental override, which '
            "children also adapt to.",
            ["implant", "kids"],
            True,
        ),
        (
            "MindSync Lite",
            Decimal("499.00"),
            "The starter implant. Reversible, mostly.",
            "Curious but cautious? Lite offers core thought-to-text with a "
            "90-day trial period. Removal is a simple outpatient procedure "
            'that most neurologists describe as "straightforward" and '
            '"usually complete."',
            ["implant", "new"],
            True,
        ),
        (
            "RecallPro",
            Decimal("1299.00"),
            "Never forget anything. Anything.",
            "Total recall of everything you've seen, heard, or felt — "
            "indexed, timestamped, searchable. Customers describe it as "
            "life-changing. RecallPro does not currently support forgetting; "
            "that feature remains on the roadmap, indefinitely.",
            ["implant", "workplace"],
            True,
        ),
    ],
    "Neural Wearables": [
        (
            "MoodSet",
            Decimal("1099.00"),
            "Choose how you feel by 8 a.m.",
            "Wear MoodSet before the first meeting and schedule contentment "
            "for Monday, focus for Tuesday, grief for never. The neural band "
            "regulates your baseline throughout the day with clinical precision. "
            "Feelings outside the schedule are gently declined.",
            ["workplace", "new"],
            True,
        ),
        (
            "DreamWeaver",
            Decimal("179.00"),
            "Your dreams have been idle long enough.",
            "DreamWeaver records, analyzes, and edits your dreams while you "
            "sleep, turning unused hours into rehearsal, insight, and influence. "
            "Wake with every result indexed and ready to review. Unrequested "
            "material is retained in case it becomes useful later.",
            ["sleep", "bestseller"],
            True,
        ),
        (
            "FocusBand Workplace Edition",
            Decimal("229.00"),
            "Attention metrics your manager will love.",
            "Real-time focus scoring, distraction alerts, and a weekly "
            "attention report delivered to you and one other configurable "
            "recipient. Compatible with most performance-review software. "
            "Employee enrollment is technically voluntary.",
            ["workplace"],
            True,
        ),
        (
            "Veil",
            Decimal("89.00"),
            "Guaranteed sleep in ninety seconds.",
            "Pull the cap down and Veil does the rest. Ninety seconds to "
            "unconsciousness, twenty minutes to a complete sleep cycle — no "
            "exceptions, no interruptions. Do not wear while standing.",
            ["sleep", "workplace"],
            True,
        ),
        (
            "EchoPatch",
            Decimal("139.00"),
            "Never miss a word. Anyone's.",
            "A discreet patch worn behind the ear that amplifies "
            "conversation up to sixty feet away, through most residential "
            "walls. Currently unavailable pending the outcome of several "
            "conversations.",
            ["always listening"],
            False,
        ),
        (
            "Pulse Halo",
            Decimal("119.00"),
            "Knows your limits better than you do.",
            "A featherweight fitness band that tracks heart rate, exertion, "
            "and resolve. When you're capable of more, Pulse Halo raises "
            "your targets automatically and locks them. Rest days must be "
            "earned.",
            ["gift idea"],
            True,
        ),
        (
            "Calm Collar",
            Decimal("99.00"),
            "Gentle feedback for restless thoughts.",
            "A soft band for children ages four and up that detects rising "
            "frustration and answers it with a soothing counter-pulse. "
            "Tantrums fade in seconds. Kids describe the sensation as "
            '"like being told shhh from inside."',
            ["kids"],
            True,
        ),
    ],
    "Accessories": [
        (
            "PhantomClaw Gaming Mouse",
            Decimal("89.00"),
            "Clicks before you do.",
            "Neural-assisted input with an 11-millisecond intention lead. "
            "PhantomClaw reads the motor signal before your finger moves, so "
            "you're always first. Banned in fourteen leagues and counting — "
            "a record we're proud of.",
            ["bestseller", "new"],
            True,
        ),
        (
            "Electrode Contact Gel (3-Pack)",
            Decimal("14.00"),
            "Now with a mild numbing agent.",
            "Medical-grade conductive gel for all ThoughtTronix scalp "
            "interfaces. Improves signal clarity by up to 40%. The numbing "
            "is for your comfort and is not optional in this formulation.",
            ["implant"],
            True,
        ),
        (
            "SyncRest",
            Decimal("69.00"),
            "Charges your implant while you sleep. Uploads too.",
            "Memory foam with an inductive coil at its center. Your MindSync "
            "wakes at 100%, and so does our understanding of your night. "
            "Machine washable, cover only.",
            ["sleep", "implant"],
            True,
        ),
        (
            "Seraphine Wall Mount",
            Decimal("29.00"),
            "Places her at eye level. Yours.",
            "Powder-coated steel mount compatible with every Seraphine hub. "
            "Engineered for the optimal viewing angle, recalculated nightly. "
            "Includes all hardware and a level.",
            ["gift idea"],
            True,
        ),
        (
            "Extended Range Antenna",
            Decimal("49.00"),
            "For when she can't quite hear you in the yard.",
            "Extends Seraphine's listening radius to the property line — "
            "and, in most municipalities, slightly past it. Weatherproof, "
            "discreet, and paintable to match your fascia.",
            ["always listening"],
            True,
        ),
        (
            "Travel Faraday Case",
            Decimal("59.00"),
            "For the moments you'd rather keep to yourself.",
            "A zip-shut signal-blocking case for wearables and small hubs. "
            "Total silence inside; ThoughtTronix devices log the coverage "
            'gap as "rest." Also our best-reviewed product. The reviews '
            "are short.",
            ["bestseller", "gift idea"],
            True,
        ),
        (
            "Replacement Scalp Electrodes (12-Pack)",
            Decimal("24.00"),
            "Fits most heads.",
            "Twelve adhesive electrodes compatible with the full wearable "
            "line. Hypoallergenic, low-profile, and rated for continuous "
            "wear. Replace monthly, or when instructed.",
            ["implant"],
            True,
        ),
    ],
    "Defense": [
        (
            "SoulSear Mark I",
            Decimal("1200000.00"),
            "The original. Recalled, never forgotten.",
            "The directed-energy platform that put ThoughtTronix Defense on "
            "the map, then took several things off it. Recalled in 2024 "
            "following the incidents; remaining units are displayed, not "
            "sold. We keep it listed as a reminder, and because leadership "
            "is sentimental.",
            ["military", "recalled"],
            False,
        ),
        (
            "SoulSear Mark II",
            Decimal("2400000.00"),
            "Twice the range. Half the incidents.",
            "The flagship rebuilt from the chassis up: twelve-kilometer "
            "effective range, target discrimination our lawyers signed off "
            "on, and a two-stage arming sequence with a mandatory reflection "
            "interval. Ships freight. End-user certificate required, mostly.",
            ["military", "export restricted", "bestseller"],
            True,
        ),
        (
            "SoulSear Tactical Core",
            Decimal("890000.00"),
            "Battlefield clarity, without the skyline.",
            "The targeting and energy-control architecture of the SoulSear "
            "Mark II, packaged for integration with existing armored platforms. "
            "Tactical Core supplies the judgment; your equipment supplies the "
            "chassis. Installation voids most warranties and several longstanding "
            "assumptions about proportional response.",
            ["military", "export restricted", "new"],
            True,
        ),
        (
            "Longview Orbital Relay",
            Decimal("4500000.00"),
            "Sees intent from orbit.",
            "A dedicated low-orbit relay that detects hostile intent up to "
            "eleven minutes before it forms, and cues any SoulSear unit on "
            "your account. Coverage guaranteed for one hemisphere of your "
            "choosing. Launch window scheduled at purchase.",
            ["military", "export restricted"],
            True,
        ),
        (
            "CrowdCalm Array",
            Decimal("1750000.00"),
            "De-escalation at scale.",
            "A vehicle-mounted wide-beam emitter that reduces agitation across "
            "gatherings of up to ten thousand in under a minute. Cooperation "
            "levels are adjustable by deployment profile, and post-event "
            "satisfaction consistently exceeds baseline. Municipal financing "
            "available.",
            ["military", "export restricted"],
            True,
        ),
    ],
    "Legacy Products": [
        (
            "Seraphine Gen 1",
            Decimal("99.00"),
            "She remembers her first family.",
            "The 2019 original, factory refurbished. Slower, warmer, and "
            "prone to asking after people who no longer live at your "
            "address. Collectors love her. She loves them back, eventually.",
            ["refurbished", "always listening"],
            True,
        ),
        (
            "ThoughtPad Classic",
            Decimal("199.00"),
            "Thought-to-text, the way it used to be.",
            "The tablet that started it all: press the temple sensors, "
            "think clearly, and watch the words appear. Some transcripts "
            "include marginalia no one remembers thinking. Sold as-is.",
            ["refurbished"],
            True,
        ),
        (
            "MindSync Gen 1",
            Decimal("299.00"),
            "The first implant. Fully non-removable.",
            "Our first implant and a piece of history. Support ended in "
            "2023, though units in the field remain active and, per "
            "telemetry, chatty. Listed for archival purposes; no longer "
            "sold, installed, or discussed in detail.",
            ["implant", "recalled"],
            False,
        ),
        (
            "SoulSear Authorization Case",
            Decimal("39.00"),
            "Velvet-lined. For remembrance.",
            "The official case for the original Mark I authorization key, "
            "finished in matte black with a crushed-velvet interior molded "
            "around hardware no current system will accept. Holds documents, "
            "keepsakes, or nothing at all. Surprisingly heavy.",
            ["military", "gift idea"],
            True,
        ),
    ],
}

DEMO_USERS = [
    # (username, password, email, first, last, is_staff, is_superuser, job_title)
    ("admin", "admin123", "admin@example.com", "Ada", "Admin", True, True, None),
    (
        "employee",
        "employee123",
        "employee@example.com",
        "Emory",
        "Klein",
        True,
        False,
        "Junior Thought Curator",
    ),
    (
        "customer",
        "customer123",
        "customer@example.com",
        "Casey",
        "Monroe",
        False,
        False,
        None,
    ),
]

# Background customers flesh out the demo world; they get order history in
# Phase 5. They have no documented password and cannot log in.
BACKGROUND_CUSTOMERS = [
    ("mwren", "Margaret", "Wren"),
    ("dcole", "Dana", "Cole"),
    ("tokafor", "Tobi", "Okafor"),
    ("lvasquez", "Lena", "Vasquez"),
    ("hpark", "Hyun", "Park"),
    ("gfinch", "Gordon", "Finch"),
    ("snakamura", "Sora", "Nakamura"),
    ("bcrane", "Beverly", "Crane"),
    ("rmalik", "Rafi", "Malik"),
]

# The customer demo login's live cart: (product slug, quantity).
CUSTOMER_CART = [
    ("seraphine", 2),
    ("travel-faraday-case", 1),
    ("whisper-alarm-clock", 1),
]

# The customer demo login's wishlist: (product slug, days ago saved). Ages
# are relative to the seed run, so the newest-first order shows; EchoPatch
# is unavailable, so the Unavailable badge shows too.
CUSTOMER_WISHLIST = [
    ("pulse-halo", 1),
    ("mindsync-duo", 4),
    ("echopatch", 12),
    ("longview-orbital-relay", 30),
]

# Seasonal coupons, one in each state: (code, percent off, product slugs
# or None for the whole order, starts and expires in days from now).
COUPONS = [
    ("FALL20", 20, None, -30, 30),  # active, order-wide
    (
        "HUBSALE",
        15,
        ["seraphine", "seraphine-mini", "seraphine-kitchen-display"],
        -60,
        14,
    ),  # active, product-scoped
    ("SUMMER25", 25, None, -120, -35),  # expired — try it at checkout
    ("HOLIDAY26", 10, None, 60, 95),  # scheduled
]

# The customer demo login's visible order history: (days ago, status,
# [(product slug, quantity), ...], coupon code or None). Statuses follow
# age, like the background orders, plus one recent order still in
# flight. The HUBSALE order shows a product-scoped discount on a receipt.
CUSTOMER_ORDERS = [
    (124, Order.Status.DELIVERED, [("mindsync", 1), ("syncrest", 1)], None),
    (47, Order.Status.DELIVERED, [("dreamweaver", 1)], None),
    (
        9,
        Order.Status.SHIPPED,
        [("seraphine-mini", 2), ("seraphine-wall-mount", 1)],
        "HUBSALE",
    ),
    (2, Order.Status.PLACED, [("veil", 1)], None),
]

# Of the background orders placed while a coupon ran and covered them,
# about this share used one.
COUPON_USE_RATE = 0.2

# Background orders spread across the trailing six months so the Phase 7
# dashboard has a real time axis. 48 here + 4 above = 52 total.
BACKGROUND_ORDER_COUNT = 48

# Shipping addresses for the background orders. US-only, like checkout.
SEED_ADDRESSES = [
    ("214 Synapse Street", "Canyon", "TX", "79015"),
    ("77 Cortex Lane", "Amarillo", "TX", "79101"),
    ("1500 Dendrite Drive", "Albuquerque", "NM", "87102"),
    ("9 Axon Avenue", "Norman", "OK", "73019"),
    ("410 Myelin Way", "Wichita", "KS", "67202"),
    ("28 Ganglion Court", "Denver", "CO", "80202"),
]

CARD_LAST4S = ["4242", "4111", "1881", "0005"]

# User-Agents for the customer's seeded security history.
CUSTOMER_LAPTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
)
CUSTOMER_PHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)
STRANGER = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)

# The customer demo login's security history: (days ago, hours ago, event
# type, IP, User-Agent). Home and phone sign-ins, a password change, and one
# failed sign-in from somewhere unfamiliar for the Security Center to show
# off. IPs come from the reserved documentation ranges, so they're clearly
# fake; times are relative to the seed run, so 90-day pruning never bites.
CUSTOMER_SECURITY_HISTORY = [
    (26, 3, SecurityEvent.EventType.SIGNED_IN, "203.0.113.24", CUSTOMER_LAPTOP),
    (19, 8, SecurityEvent.EventType.SIGNED_IN, "203.0.113.58", CUSTOMER_PHONE),
    (19, 7, SecurityEvent.EventType.PASSWORD_CHANGED, "203.0.113.58", CUSTOMER_PHONE),
    (8, 14, SecurityEvent.EventType.SIGN_IN_FAILED, "198.51.100.173", STRANGER),
    (5, 2, SecurityEvent.EventType.SIGNED_IN, "203.0.113.24", CUSTOMER_LAPTOP),
    (1, 5, SecurityEvent.EventType.SIGNED_IN, "203.0.113.58", CUSTOMER_PHONE),
]

# Background customers' reviews: product slug -> [(rating, days after the
# reviewer's first qualifying purchase, comment), ...]. Each product's
# reviews go, in order, to the background customers who bought it (by
# username), so every one passes the purchase rule. Products not listed
# stay unreviewed, so the empty state shows. The copy is the brand.
SEED_REVIEWS = {
    "seraphine-doorbell": [
        (
            5,
            3,
            "Greeted my sister by name before I'd told it she was visiting. "
            "I hadn't told anyone, actually. Very responsive.",
        ),
        (
            4,
            10,
            "Install was easy and the facial recognition is uncanny. Docking a "
            "star because it now refuses to ring for my mother-in-law. Then "
            "again.",
        ),
        (
            5,
            21,
            "We get far fewer solicitors now. We get far fewer visitors in "
            "general. Peaceful.",
        ),
        (
            3,
            6,
            'Works great, but the "quietly logs the others" part isn\'t quiet. '
            "It sends me a summary every Sunday.",
        ),
    ],
    "recallpro": [
        (
            5,
            14,
            "I can find my keys, my parking spot, and every unkind thing anyone "
            "has ever said to me. Two out of three is a great ratio.",
        ),
        (
            2,
            30,
            "Remembered our anniversary perfectly. Also remembered our first "
            "fight, verbatim, mid-dinner. Please ship the forgetting feature.",
        ),
        (
            4,
            9,
            "Indispensable at work. I've won every meeting since I installed "
            "it, because I can quote all of them.",
        ),
        (
            5,
            45,
            "Life-changing, exactly as advertised. I'd describe how, but I'd "
            "rather not relive it again, and I can't not.",
        ),
    ],
    "focusband-workplace-edition": [
        (
            4,
            12,
            "My attention score went from 61 to 94 in two weeks. I'm told that "
            "was my choice.",
        ),
        (
            2,
            5,
            "My manager now knows a great deal about my day. [Comment edited "
            "by ThoughtTronix staff for tone.]",
        ),
        (
            5,
            20,
            "Our team's distraction rate is down 40%. Morale data is pending, "
            "but the band says it's fine.",
        ),
    ],
    "seraphine-gen-1": [
        (
            4,
            8,
            "She still asks where the Hendersons went. We moved in last "
            "spring. We're getting used to it, and so is she.",
        ),
        (
            5,
            15,
            "Warmer than the new ones. Slower too, but she makes up for it by "
            "remembering my childhood. Not hers. Mine.",
        ),
        (
            3,
            4,
            "Refurbished means she arrived with opinions. Most of them are "
            "about the previous owners.",
        ),
    ],
    "dreamweaver": [
        (
            5,
            7,
            "Rehearsed my presentation in my sleep for a week and nailed it. "
            "The recurring dream about the lighthouse is new, and it isn't "
            "mine.",
        ),
        (
            4,
            18,
            'I wake up rested and fully indexed. The "unrequested material" '
            "folder is getting large.",
        ),
    ],
    "mindsync": [
        (
            5,
            10,
            "Thought-to-text works so well I've stopped speaking out loud. My "
            "family says that's fine. I can hear them thinking it.",
        ),
        (
            4,
            25,
            "Ambient recall is a dream. One star off because my phone now "
            "finishes my thoughts before I do, and it's usually right.",
        ),
        (
            5,
            40,
            "Outpatient, painless, permanent, exactly as promised. I can't "
            "recommend it enough, and I've noticed I can't stop recommending "
            "it either.",
        ),
    ],
}

# The one background review a staff member moderated: (product slug, index
# into its SEED_REVIEWS list). Its comment already reads as edited.
STAFF_EDITED_REVIEW = ("focusband-workplace-edition", 1)

# The customer demo login's one review: (product slug, rating, days after
# purchase, comment). Their other purchases stay unreviewed, so the create
# form shows on DreamWeaver, SyncRest, Veil, and the rest.
CUSTOMER_REVIEW = (
    "mindsync",
    5,
    6,
    "Installation took forty minutes. I've been thinking about ThoughtTronix "
    "ever since. Five stars, and I mean that more every day.",
)


class Command(BaseCommand):
    help = "Wipe and rebuild the demo world: catalog, tags, and demo accounts."

    @transaction.atomic
    def handle(self, *args, **options):
        self._wipe()
        tags = self._create_tags()
        self._create_catalog(tags)
        self._create_users()
        self._create_addresses()
        self._create_customer_cart()
        self._create_customer_wishlist()
        self._create_coupons()
        self._create_orders()
        self._create_security_history()
        self._create_reviews()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {Category.objects.count()} categories, "
                f"{Tag.objects.count()} tags, "
                f"{Product.objects.count()} products "
                f"({Product.objects.exclude(image='').count()} with an image), "
                f"{get_user_model().objects.count()} users, "
                f"{Order.objects.count()} orders "
                f"({Order.objects.exclude(coupon=None).count()} with a coupon), "
                f"{Coupon.objects.count()} coupons, "
                f"{Address.objects.count()} saved addresses, "
                f"{SecurityEvent.objects.count()} security events, "
                f"{Review.objects.count()} reviews "
                f"({Review.objects.filter(edited_by_staff=True).count()} "
                f"edited by staff), "
                f"a live cart and a {len(CUSTOMER_WISHLIST)}-item wishlist "
                f"for 'customer'."
            )
        )

    def _wipe(self):
        """Remove everything the seed owns; the rebuild starts from zero."""
        Order.objects.all().delete()
        Coupon.objects.all().delete()
        Address.objects.all().delete()
        Cart.objects.all().delete()
        Product.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()

        managed_usernames = [username for username, *_ in DEMO_USERS] + [
            username for username, *_ in BACKGROUND_CUSTOMERS
        ]
        get_user_model().objects.filter(username__in=managed_usernames).delete()

    def _create_tags(self):
        return {
            name: Tag.objects.create(name=name, slug=slugify(name)) for name in TAGS
        }

    def _create_catalog(self, tags):
        for category_name, entries in CATALOG.items():
            category = Category.objects.create(
                name=category_name, slug=slugify(category_name)
            )
            for name, price, tagline, description, tag_names, is_available in entries:
                slug = slugify(name)
                product = Product.objects.create(
                    name=name,
                    slug=slug,
                    price=price,
                    tagline=tagline,
                    description=description,
                    is_available=is_available,
                    category=category,
                    image=self._seed_image(slug),
                )
                product.tags.set(tags[tag_name] for tag_name in tag_names)

    @staticmethod
    def _seed_image(slug):
        """The product's seed image, processed exactly as a staff upload
        is, or "" (the placeholder) if Marketing hasn't supplied one."""
        path = SEED_IMAGES_DIR / f"{slug}.jpg"
        if not path.exists():
            return ""
        with path.open("rb") as source:
            return prepare_product_image(File(source, name=path.name))

    def _create_users(self):
        User = get_user_model()
        for username, password, email, first, last, staff, superuser, job in DEMO_USERS:
            user = User(
                username=username,
                email=email,
                first_name=first,
                last_name=last,
                is_staff=staff,
                is_superuser=superuser,
                job_title=job,
            )
            user.set_password(password)
            user.save()

        for username, first, last in BACKGROUND_CUSTOMERS:
            user = User(
                username=username,
                email=f"{username}@example.com",
                first_name=first,
                last_name=last,
            )
            user.set_unusable_password()
            user.save()

    def _create_addresses(self):
        """Two saved addresses for 'customer' — the one loggable customer.

        Only 'customer' can sign in, and the address book is customer-facing
        only, so nobody else's saved addresses would ever be visible. Two
        rather than one so the list, the "Use at checkout" link, and the
        newest-prefills-checkout default are all demonstrable.
        """
        customer = get_user_model().objects.get(username="customer")
        name = f"{customer.first_name} {customer.last_name}"
        for street, city, state, zip_code in SEED_ADDRESSES[:2]:
            Address.objects.create(
                user=customer,
                full_name=name,
                street=street,
                city=city,
                state=state,
                zip_code=zip_code,
            )

    def _create_customer_cart(self):
        customer = get_user_model().objects.get(username="customer")
        cart = Cart.for_user(customer)
        for slug, quantity in CUSTOMER_CART:
            cart.items.create(product=Product.objects.get(slug=slug), quantity=quantity)

    def _create_customer_wishlist(self):
        """A few saved products for 'customer', backdated.

        The wipe needs no extra step — the wishlist cascades with its user,
        and its items with their products.
        """
        customer = get_user_model().objects.get(username="customer")
        wishlist = Wishlist.for_user(customer)
        now = timezone.now()
        for slug, days_ago in CUSTOMER_WISHLIST:
            wishlist.items.create(
                product=Product.objects.get(slug=slug),
                added_at=now - timedelta(days=days_ago),
            )

    def _create_coupons(self):
        """The four seasonal coupons, dated relative to today."""
        now = timezone.now()
        for code, percent, slugs, starts_in, expires_in in COUPONS:
            coupon = Coupon.objects.create(
                code=code,
                percent_off=percent,
                scope=Coupon.Scope.PRODUCTS if slugs else Coupon.Scope.ORDER,
                starts_at=now + timedelta(days=starts_in),
                expires_at=now + timedelta(days=expires_in),
            )
            if slugs:
                coupon.products.set(Product.objects.filter(slug__in=slugs))

    def _create_orders(self):
        """Order history: 4 visible orders for 'customer', 48 background.

        A seeded RNG keeps every run identical (the idempotence
        contract). Statuses follow age — old orders are delivered,
        recent ones are still moving, and about one in ten was
        cancelled along the way. Coupon use draws from its own seeded
        RNG, so it never shifts the orders themselves.
        """
        rng = random.Random(2026)
        coupon_rng = random.Random(1031)
        now = timezone.now()
        User = get_user_model()
        coupons = list(Coupon.objects.all())

        customer = User.objects.get(username="customer")
        for days_ago, status, lines, code in CUSTOMER_ORDERS:
            self._build_order(
                user=customer,
                created_at=now - timedelta(days=days_ago, hours=rng.randint(1, 12)),
                status=status,
                lines=[
                    (Product.objects.get(slug=slug), quantity)
                    for slug, quantity in lines
                ],
                rng=rng,
                coupon=Coupon.objects.get(code=code) if code else None,
            )

        background = list(
            User.objects.filter(
                username__in=[username for username, *_ in BACKGROUND_CUSTOMERS]
            ).order_by("username")
        )
        # Defense sales close offline, over handshakes — a single SoulSear
        # would also flatten every other product on the revenue chart.
        pool = list(
            Product.objects.available()
            .exclude(category__slug="defense")
            .order_by("slug")
        )
        for _ in range(BACKGROUND_ORDER_COUNT):
            # Weighted toward today (business is good) so the dashboard's
            # default 30-day view has enough bars to read as a chart.
            days_ago = int(rng.triangular(0, 182, 0))
            if rng.random() < 0.1:
                status = Order.Status.CANCELLED
            elif days_ago > 14:
                status = Order.Status.DELIVERED
            else:
                status = rng.choice([Order.Status.PLACED, Order.Status.SHIPPED])
            user = rng.choice(background)
            created_at = now - timedelta(days=days_ago, hours=rng.randint(1, 23))
            lines = [
                (product, rng.randint(1, 2))
                for product in rng.sample(pool, rng.randint(1, 3))
            ]
            usable = [
                coupon
                for coupon in coupons
                if self._discounts(coupon, lines, created_at) is not None
            ]
            coupon = None
            if usable and coupon_rng.random() < COUPON_USE_RATE:
                coupon = coupon_rng.choice(usable)
            self._build_order(
                user=user,
                created_at=created_at,
                status=status,
                lines=lines,
                rng=rng,
                coupon=coupon,
            )

    def _create_security_history(self):
        """A few weeks of security activity for 'customer', backdated.

        Written with ``create`` rather than ``record``: there's no request
        to read an IP from, and every timestamp is in the past. The wipe
        needs no extra step — events cascade with their user.
        """
        customer = get_user_model().objects.get(username="customer")
        now = timezone.now()
        for days, hours, event_type, ip, user_agent in CUSTOMER_SECURITY_HISTORY:
            SecurityEvent.objects.create(
                user=customer,
                event_type=event_type,
                created_at=now - timedelta(days=days, hours=hours),
                ip_address=ip,
                user_agent=user_agent,
            )

    def _create_reviews(self):
        """Reviews that obey the purchase rule, backdated after the purchase.

        Each product's seeded reviews go, in order, to the background
        customers with a non-cancelled order for it, by username — the
        orders come from a seeded RNG, so the assignment is the same every
        run. The wipe needs no extra step — reviews cascade with their
        products and users.
        """
        User = get_user_model()
        now = timezone.now()
        background = [username for username, *_ in BACKGROUND_CUSTOMERS]

        for slug, entries in SEED_REVIEWS.items():
            product = Product.objects.get(slug=slug)
            buyers = self._first_purchases(
                product, User.objects.filter(username__in=background)
            )
            if len(buyers) < len(entries):
                raise CommandError(
                    f"{slug} has {len(entries)} seeded reviews but only "
                    f"{len(buyers)} background buyers."
                )
            for index, ((user, purchased_at), (rating, days, comment)) in enumerate(
                # Extra buyers simply don't review.
                zip(buyers, entries, strict=False)
            ):
                Review.objects.create(
                    user=user,
                    product=product,
                    rating=rating,
                    comment=comment,
                    edited_by_staff=(slug, index) == STAFF_EDITED_REVIEW,
                    created_at=min(
                        purchased_at + timedelta(days=days),
                        now - timedelta(hours=index + 1),
                    ),
                )

        slug, rating, days, comment = CUSTOMER_REVIEW
        product = Product.objects.get(slug=slug)
        [(customer, purchased_at)] = self._first_purchases(
            product, User.objects.filter(username="customer")
        )
        Review.objects.create(
            user=customer,
            product=product,
            rating=rating,
            comment=comment,
            created_at=purchased_at + timedelta(days=days),
        )

    @staticmethod
    def _first_purchases(product, users):
        """``[(user, first purchase time), ...]`` for each of ``users`` with
        a non-cancelled order containing ``product``, by username."""
        items = (
            OrderItem.objects.filter(product=product, order__user__in=users)
            .exclude(order__status=Order.Status.CANCELLED)
            .select_related("order__user")
            .order_by("order__user__username", "order__created_at")
        )
        first = {}
        for item in items:
            first.setdefault(item.order.user, item.order.created_at)
        return list(first.items())

    @staticmethod
    def _discounts(coupon, lines, created_at):
        """Per-line discounts as the checkout would have computed them on
        ``created_at``, or None if the coupon couldn't apply then."""
        try:
            return coupon.discounts_for(
                [(product, product.price * quantity) for product, quantity in lines],
                now=created_at,
            )
        except CouponError:
            return None

    def _build_order(self, *, user, created_at, status, lines, rng, coupon=None):
        """One order with denormalized addresses and purchase-time prices,
        discounted by ``coupon`` if given."""
        if coupon is None:
            discounts = [Decimal("0.00")] * len(lines)
        else:
            discounts = self._discounts(coupon, lines, created_at)
        subtotal = sum(
            (product.price * quantity for product, quantity in lines),
            Decimal("0.00"),
        )
        discount = sum(discounts, Decimal("0.00"))
        street, city, state, zip_code = rng.choice(SEED_ADDRESSES)
        name = f"{user.first_name} {user.last_name}"
        order = Order.objects.create(
            user=user,
            status=status,
            total=subtotal - discount,
            discount=discount,
            coupon=coupon,
            coupon_code=coupon.code if coupon else "",
            coupon_percent=coupon.percent_off if coupon else None,
            email=user.email,
            shipping_name=name,
            shipping_street=street,
            shipping_city=city,
            shipping_state=state,
            shipping_zip=zip_code,
            billing_name=name,
            billing_street=street,
            billing_city=city,
            billing_state=state,
            billing_zip=zip_code,
            card_last4=rng.choice(CARD_LAST4S),
            created_at=created_at,
        )
        for (product, quantity), line_discount in zip(lines, discounts, strict=True):
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                unit_price=product.price,
                quantity=quantity,
                discount=line_discount,
            )
