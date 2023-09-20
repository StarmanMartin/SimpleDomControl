Core of SDC
===========




The Django app **sdc_manager** contains the following elements:


The files *consumer.py* and *routing.py* manage the websocket requests. Usually, you do not need to change these files. The file *app.py* is the default app Django file. The *urls.py* file ensures that the foundation, index.html, is served to the client. The *index.html* is in *mysite/templates/sdc_core/index.html*. Note, that the *index.html* is the foundation of your website. Hence, it has to be changed. As a counterpart to the *index.html* there is *style.css* change this file for basic style elements. The file *main.organizer.js* is the basic root js file. This file is updated automatically. Finally the folder *simpleDomControl* contains all client js parts of SDC.