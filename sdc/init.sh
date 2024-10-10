virtualenv venv
source venv/bin/activate
pip install django
pip install simpledomcontrol


echo $PROJECT_NAME

django-admin startproject $PROJECT_NAME .

sed -i "s/INSTALLED_APPS = \[/INSTALLED_APPS = ['sdc_core',/g" ./$PROJECT_NAME/settings.py
sed -i "s/'DIRS'\: \[\]/'DIRS'\: \[BASE_DIR \/ 'templates'\]/g" ./$PROJECT_NAME/settings.py
python manage.py sdc_init
cd ./Assets
npm install