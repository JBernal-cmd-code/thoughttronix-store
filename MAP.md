The question from the "Three Question of Your Own" that I chose. 

The question I decided to include in my map was "If a customer's is successfully able to purchase a product, but decides to cancel the order, is there a specfic file or code setup to handle that process?"

After asking this question, Claude explained that there isn't really a customer-facing cancellation option. However, there is a cancellation process that staff can set from the. Essentially Claude explained that there isn't a traditional cancel button or option that a customer would have access to. This is also the same for employees, there is no button or option to just cancel an order. But an employee instead can click into an order, which then renders OrderStatusForm as a dropdown next to whichever order they chose. From here, the employee can choose "Cacelled" from the dropdown, which then gets submitted to UpdateOrderStatusView.post and saves the order status as canceled. So you can't really cancel an order, but you can mark its status as cancelled and it will have the same affect. 

Map Questions: 

1. 

There are 4 apps in this project. 

First is accounts, which handles identity and access. 

Second is products, which handles the catalog. 

Third is orders, this handles everything from the cart up to the process of ordering from the cart.

Fourth is dashboard, this centralizes around staff analytics. 

2. 

The path I chose is GET /, which is the path to the home page of the catalog. This first starts at ROOT_URLCONF and goes through urlpatterns. The request then goes through products/urls.py:8 and then to the view of both products/views.py:20 and CatalogView. From this, the request then processes through the templates at templates/products/catalog.html and finally stops when the resposne is rendered back through the browser. 

3. 

I chose the Cart model, which represents the shopping cart of a customer who is signed in. One method I found to be interesting was for_user(user), which essentially is a check or call to see if there is a cart row already exists with a user. If no row found, a mew cart is inserted and return, but if a cart is found, the existing cart is fetched and returned.

4. 

Based on what Claude mentioned, a category can't be deleted while it has products, so nothing would happen to the products as the delete is refused. The line that decides this is products/models.py:70

5. 

From the questions I asked, it was mentioned that there is no separate tests/ directory, but tests are instead organized in each app, next to the code that they cover. Additionally, pytest is used to discover each one of these tests through pyproject.toml:21: python_files = ["tests.py", "test_*.py"]. 

6. 

I think the one thing still unclear to me is how the tests are setup for this project. If I am correct, the past 3 weeks the tests we've seen have all been stored in one file, I believe we usually called it tests.py, but this project doesn't have a separate file but instead implements the tests into each appm, basically separating the test code. I understand why this would be easier in the long run if you have a lot of code and one to test one as you go, but wouldn't it also be easier just to have one file where you store tests and can update it as you continue with your code? Additionally, wouldn't doing this elimiate the need for the conftest.py code? 
