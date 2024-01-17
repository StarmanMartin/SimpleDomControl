What is SDC
===========


SDC is a framework that combines elements of both the MVC (Model-View-Controller) and MVT (Model-View-Template) patterns. Its main goal is to provide a tool for simple and efficient web development. The name 'SDC' is an abbreviation for 'Simple DOM Control,' indicating its focus on controlling and manipulating the Document Object Model (DOM), which is crucial for web development, particularly in dynamic web pages.

Unlike other frameworks, SDC is closely integrated with the Python-based Django framework. This design decision enhances development support and performance. In conjunction with JavaScript, SDC offers an ideal environment for rapidly creating web applications with enhanced functionality and interactivity.



**Django Server**: Django is a Python web framework that follows the Model-View-Controller (MVC) design pattern, or more precisely, the Model-View-Template (MVT) pattern. In this pattern:

**Model**: Django's models represent the data structure of your application and typically map to your database tables.


**View**: In Django, views handle the logic for processing requests from clients and returning responses. They can also be considered as the Controller in the MVC pattern.

**Template**: Templates in Django are responsible for generating HTML pages and rendering data to be displayed. They are similar to the View in the MVC pattern.

**Client with Controller (JavaScript)**: On the client-side, you're using JavaScript for your controller logic. This can follow the Model-View-Controller (MVC) or Model-View-ViewModel (MVVM) pattern, depending on how you structure your client-side code. The JavaScript controller interacts with the server through HTTP requests (possibly using AJAX or Fetch) to fetch and send data.

**DOM**: HTML elements represent the View in your client-side architecture. They define the structure of the user interface and are manipulated by JavaScript to update the UI dynamically.

**Models via Socket Connected to DB Entries**: This part involves real-time communication with a database using sockets. This can be seen as an implementation of the Real-Time Database Sync pattern, which combines aspects of the Observer and Publisher-Subscriber patterns. When data changes in the database, it is pushed to connected clients via sockets, ensuring real-time updates without the need for constant polling.

In summary, the architecture combines elements of several design patterns:

Django uses the Model-View-Template (MVT) pattern on the server-side.
JavaScript on the client-side can follow the Model-View-Controller (MVC) or Model-View-ViewModel (MVVM) pattern.
Real-time communication with sockets for database updates can be considered a form of the Real-Time Database Sync pattern.
Overall, this architecture is designed to create a responsive and real-time web application that efficiently handles data flow between the server and clients.




