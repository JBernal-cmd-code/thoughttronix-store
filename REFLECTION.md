## Account Security Center

1.

The phase I chose to write about is phase 2, which is "Forgot Password, end to end". Once this phase is up, the working behavior is that if a customer forgets their password, they'll have the option to request a link to change their password that is sent to their email. That link can only be used once to set a new password. I verified that this worked by running the server and going to the sign-in page while signed out. I clicked on "Forgot your password?" on the sign-in page and used customer@example.com as my email. From here, a link was posted in the terminal that I copied into my browser and it took me to the reset password page. From here I changed the password from customer123 to fresh-synapse-4242. After entering my new password twice, I was taken back to the login page and a message towards the top of the sign in prompt confirmed my password was reset. I logged in with the new password and I was able to log in successfully. I also tested a few things that should not work. When I pasted the same link again, it said the link doesn't work, so it really only works once. When I typed 123 as the new password, I got errors saying it was too short and too common. I also tried the forgot password page with nobody@example.com and employee@example.com, and it showed the same page but no email showed up in the terminal. This is how I confirmed that the phase was implemented properly and that I did not need to go back and ask Claude for any changes.

2.

Looking back at Understanding Authentication, the first Django authentication component I found is LoginView. It's located in accounts/views.py on line 47, the full line is class SignInView(LoginView):. I chose this because LoginView is a built-in sign in view in Django. In my project, it takes username and password, and will check them, aand if they're both correct it will sign the user in and start a new session. This matches the lesson from Understanding Authentication as this same line of code was used in the lesson, both being used to allow people to signin with a username. The second component I chose is LoginRequiredMixin. This line is located in accounts/views.py on line 125. The full line is class SecurityCenterView(LoginRequiredMixin, TemplateView):. From this line, LoginRequiredMixin checks if a user is signed in, and if they're not, it will send the user to the sign in page. This matches the authentication pattern from the lesson. The lesson explained that during sign in, Django creates a session and the browser sends a cookie with every page after that, so Django knows who the user is through request.user. LoginRequiredMixin uses request.user to check if a user is signed in, which is how it knows whether to let a user into the Security page or send a user to sign in.

3.

I chose password change for this question. Similar to question, password change is in accounts/views.py and is on line 136. It is class ChangePasswordView(LoginRequiredMixin, PasswordChangeView):. This line is a built in Django view for handling password changes. It checks that the old password is correct, runs the password rules on attempted new passwords, and saves the new password as a hash once accepted. This matches the pattern from Password Managment in the sense that the lesson said a passord change should follow Django's built in password framwork instead of just writing your own password code handler. The only real difference from the lessons and my project is that in the lesson, PasswordChangeDoneView is the page that shows once a passowrd is changed. In my project, the page shown after a changed password is the security page with a message that confirms the password has been changed. I accepted this differnce since the security page is where the user initially is at and doesn't really need another page just for confirmation.

4.

For the last question, I went with phase 5, "Security activity, sign ins". This phase added the SecurityEvent model only connects to one event, which is successful sign ins, which then shows those events on the security page. Once this phase was done, I was able to sign in as a customer, go to the security and see a signed in row with the time, my device, and my IP. It did the same for when I signed in from Incognito window, creating a new row. Logging in with a different customer account and employee account would only show the sign ins for that user and not the others. This was a useful stopping point since the activity log was confirmed to work with just one simple event before anything else was added. When the plan was being made, Claude asked if phase 5 and 6 should merge, but I chose to keep them separate to confirm that activity logs were correctly. Then in phase 6, if anything did not work right, I'd be able to fix the problem in the new events and not the activity log itself.





## Product Images

Question 1. 

For question 7 of grill me, Claude asked what to do with the fourt images that had text baked into them. Claude recommened keeping placeholders on those products until Marketing sent versions without text. I disagreed with this because marketing had mentioned that placeholders tested poorly with customers. I chose to use all four images now and swap them later if marketing chose to later send images without text. The only thing it affected is that Claude uploaded and used all images provided.


Question 2.1  

My ImageField line was listed under products/models.py. The line is image = models.ImageField(upload_to=product_image_path, blank=True), on line 78. In my code, the upload_to value basically decides where an uploaded image is saved to and what name its given. It points to a function called product_image_path that saves each uploaded image in the media/products/ folder with a unique name based on the product's slug.
 

Question 2.2

My form to upload a product image is in templates/products/manage_product_form.html, on line 13. The line is form method="post" enctype="multipart/form-data" class="mt-2 space-y-4. The reason enctype is needed for a file upload is becasue without it, a form would send everything as one line of text. Using enctype helps the browser split the form into separate parts.



Question 3.

1 Path on disk:
C:\Users\jesus\cidm3312\thoughttronix-store\media\products\assist-headband-4500a4e3.webp
Determined by MEDIA_ROOT in config/settings.py (line 146), plus upload_to=product_image_path on the image field in products/models.py (line 78).

2 Value in the database:
products/assist-headband-4500a4e3.webp
Determined by the image ImageField (and its upload_to) in products/models.py (line 78).

3 URL the browser requests:
http://127.0.0.1:8000/media/products/assist-headband-4500a4e3.webp
Determined by MEDIA_URL in config/settings.py (line 144), plus the database value. The part of the code that makes media url work is line 29, urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT), in config/urls.py. This line works in Django by applying that any URL starting with media should be handled with the matching file from the media folder. 



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



