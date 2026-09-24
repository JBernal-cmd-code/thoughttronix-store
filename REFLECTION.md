## Discount Coupons

Quesiton 1. 

Before I answer the question, I wanted to mention that I did /clear in my initial Claude grill me session before I uplaoded it to my PROMPTS.md. That was a mistake on my part. I tried doing some research but did not find anything that mentioned that I'd be able to access my past messages after I did /clear. Moving onto the question, one decision I found interesting but that confused me from the first grill me session was when Claude asked me was if I wanted to coupons to be displayed as percentage or dollar amount, or if I wanted it as both. I believe A was percentage, B was dollar amount, and C was both. I was a bit confused by this so I asked Claude to expand on what option meant. Essentially Claude said that A would show a coupon as being 20% off an order, B would should a set dollar amount, which could be 5 dollars off, and then C would be that you could choose between either when creating the coupon. I think this decision initally confused me since I was thinking about the coupons I've seen/used and how I have only really seen percentage amounts. I ended up going with option A since I found it to be a smoother design and it fit with what I was used to.

Question 2. 

The change I made was how the products were listed in the employee/admin view in the back office when editing or adding a coupon. Initially, products would show up as all jumbled and just a string of texts that you could not choose. All products were listed, which was good, but they were jumbled and were basically just listed with no real purpose. The original choice was to have the products listed on the products side of coupons, but there was no specification of how they'd be displayed. I wanted it changed since the products looked so unorganized and truly had no real reason for being there on the first run. But after running another grill me session, I asked Claude to reorganize the products and now it works as all products listed, with spacing between them, and having the option to select and unselect certain products. This helps if the coupon applies to only certain products, and it actually now allows you to choose what product is applied. During my build, 2 tests did faill, and they were related to accounts view and models. I believe the failed tests came from during the lab when I organzed addresses alphabetically. For some reason, my code was failing because of this change. I went in and changed adddress list view and models from alpahbetical to now organizing recent to oldest. 




## Featured Products

Question 1. 

For this reflection, I did prompt Claude for help with this question to better my own understanding. Marking a product as featured in the admin interface causes the badge to appear in the storefornt through the use of a boolean process. What I mean by this is that the Product model has a boolean field (is_featured = models.BooleanField(default=False)). This first distinguishes if a product is or isn't featured. After this, the option to toggle a product as featured is provided through products/test_backoffice.py. When this is toggeled, a customer who visists the store will see when a product is listed as featured because the storefront view passes the product data to templaces in catalog.html and detail.html. The conditional check will then render the featured badge if the boolean is true.

Question 2. 

I verified that the featured badge and featured toggle worked by first running uv run python manage.py tailwind runserver. I first logged in as the admin account. From the catalog page, I clicked on "Back office" from the top right. In back office, I chose products and then scrolled down to Seraphine. Clicking edit, I scrolled down to the bottom and right below the is available toggle, I now see a is featured toggle option. I toggled is featured and saved this edit. I then logged out of admin and back into customer view. Logging into customer, and on the catalog page, I scrolled down and then clicked to page 2. Scrolling down to Seraphine, I see it now has a featured badge right next to its category. Cliking onto Seraphine, it also show a Featured badge right next  to where it says in stock.

Question 3

One challenge I did face was when wrinting my prompt for step 1. I asked Claude to make the is_featured field to product, and it ran its check and confirmed that all looked good. I logged in as admin and when I went to edit a product, I did not see the is featured option at all. I was confused since everything looked good and all the code updated, but it wasn't showing at all. I closed VS Code and reopened but the same issue. Looking back at the summary of what Claude changed, it said this: I left it out of the back-office product form and the seed data — say the word if you want either exposed. I had thought my prompt was clear to show that I would want this changed to be displayed, but it decided to not show it. I'm honestly not sure why it did that, but I did a follow up prompt and asked for it to be show, and it worked right away. I'm not sure if my prompt was unclear or if that was a default option not to show it.



