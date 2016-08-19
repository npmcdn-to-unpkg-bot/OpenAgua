# Project information

See [project info] (http://centrodelagua-decisiones.github.io/OpenAguaDSS/).

# Setup/use on local machine

## Set up Hydra Platform
* [general Hydra Platform information] (www.hydraplatform.org),
* [download from GitHub] (https://github.com/UMWRG/HydraPlatform), or
* [set up on Windows] (http://umwrg.github.io/HydraPlatform/tutorials/getting-started/server.html)

## Set up OpenAgua

There are a few settings that should be set on a machine-specific basis, whether on a local machine or on a web server. These are stored in a folder called "instance" under the top-level OpenAguaDSS folder:

1. Create an "/instance" folder.
2. In "/instance", create "config.py". This new file contains settings that will supercede settings in the main "config.py". For example, you can overwrite default debug settings, as: `DEBUG=True`.
3. At a minimum, set the following parameters (values are examples only; your settings may be different):
```
# Hydra Server settings
HYDRA_URL = 'http://127.0.0.1:8080/json'

# Flask-Mail settings
MAIL_USERNAME = 'admin@mysite.com'
MAIL_PASSWORD = 'password'
MAIL_DEFAULT_SENDER = '"OpenAgua robot" <noreply@mysite.com>'
MAIL_SERVER = 'smtp.mysite.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USE_TLS = False
```
4. Optionally, set a few other parameters as desired:
  * DEBUG
  * SECRET_KEY. This can be created in Python with the urandom function in the os. I.e. `import os` followed by `os.urandom(24)`. IMPORTANT: This should be set here in a production environment!

## Run

1. See below to set up OpenAguaDSS in your github folder.
2. For now, use Hydra Modeller to set up a test project, as follows:
  a. Create a project called "Monterrey"
  b. Import the template [WEAP.zip on GitHub] (https://github.com/rheinheimer/Hydra-WEAPTemplate).
  c. Create a network "base_network", using the WEAP template.
  d. Exit Hydra Modeller
3. Run Hydra Platform
4. Run run.py (or run.bat on Windows)
5. Go to 127.0.0.1:5000 in your web browser.
6. Log in with "admin@gmail.com" and "password".

# Setup/use on Linux as a web server

This assumes a simple configuration, whereby 1) OpenAguaDSS and Hydra Platform are run from the same machine, 2) they are both served by the same Apache2 instance. Overall Apache2 configuration is not explained here. However, the following will help get things going, and should work.

## Hydra Platform and OpenAgua configuration

Of course, Hydra Platform and OpenAgua need to be installed on the server. Installing them on the same machine may or may not be efficient. Consult a web expert! If they are installed on the same machine, they could be installed, for example, in /var/www/HydraPlatform and /var/www/OpenAguaDSS, respectively. Use git to do this.

### Hydra Platform

Aside from the general configuration needed on a linux machine as explained elsewhere, Hydra Platform needs to know where to look for the database. The default setting is to create a local SQLite database, which may or may not be desired. This can be changed in /HydraPlatform/config/hydra.ini.

### OpenAgua

In the example configurations below, Hydra Server will be available on hydra-server.mysite.com. So, OpenAgua needs to know this. In your /OpenAgua/instance/config.py file (see above), add `HYDRA_URL = 'http://hydra-server.mysite.com/json'`.

## Apache2 configuration

Hydra Platform and OpenAgua can be hosted via Apache using virtual hosts. In this example, Hydra Platform is served on hydra-server.mysite.com, while OpenAgua is served on www.mysite.com.

On Ubuntu, two separate configuration files can be prepared, both located in /etc/apache2/sites-available. Each file might be called, for example, hydra-platform.conf and openagua.conf, respectively. The configuration file for **Hydra Platform** can be as follows (this assumes HydraPlatform is located in /var/www):

```
WSGIPythonPath /var/www/HydraPlatform/HydraServer/python:/var/www/HydraPlatform/HydraLib/python

<VirtualHost *:80>
    ServerName hydra-server.mysite.com
    ServerAdmin admin@mysite.com

    WSGIScriptAlias / /var/www/HydraPlatform/HydraServer/hydra.wsgi

    WSGIDaemonProcess hydra-server user=www-data processes=1 display-name=%{GROUP} python-path=/var/www/HydraPlatform/HydraServer/$
    WSGIProcessGroup hydra-server

    <Directory /var/www/HydraPlatform/HydraServer/>
        WSGIApplicationGroup %{GLOBAL}
        Order deny,allow
        Allow from all
    </Directory>

    <LocationMatch ".*(py|pyc)$">
        Order deny,allow
        Deny from all
    </LocationMatch>
    
	ErrorLog ${APACHE_LOG_DIR}/error-hydra-server.log
    CustomLog ${APACHE_LOG_DIR}/access.log combined

    LogLevel warn
    
</VirtualHost>
```

openagua.conf, for **OpenAgua**, would look similar:

```
<VirtualHost *:80>
    ServerName www.mysite.com
    ServerAdmin admin@mysite.com

    WSGIDaemonProcess openagua user=www-data threads=5 display-name=%{GROUP}
    WSGIScriptAlias / /var/www/OpenAguaDSS/openagua.wsgi

    <Directory /var/www/OpenAguaDSS/OpenAgua/>
        WSGIProcessGroup openagua
        WSGIApplicationGroup %{GLOBAL}
        Order allow,deny
        Allow from all
    </Directory>

    <LocationMatch ".*(py|pyc)$">
        Order deny,allow
        Deny from all
    </LocationMatch>
    
	ErrorLog ${APACHE_LOG_DIR}/error-hydra-server.log
    CustomLog ${APACHE_LOG_DIR}/access.log combined

    LogLevel warn
    
</VirtualHost>
```

To understand what these actually mean, you'll have to look elsewhere. One thing to note, however, is that both of these point to a .wsgi file. These are already included with the respective distributions.

To enable these, use the command `a2ensite hydra-server` and `a2ensite openagua` (prepended with `sudo` as needed). Once these are enabled, restart Apache2 with `service apache2 restart`.

Voila! OpenAgua should now be available on www<span></span>.mysite.com, while Hydra Server should be available at hydra-server.mysite.com. This assumes, of course, you have configured your site's DNS appropriately.

Note that this configuration works on Ubuntu, which has a more advanced Apache configuration organization. There may be other configurations, depending on actual web server (i.e., not Apache) and/or machine (e.g., non-Ubuntu machines).

# Documentation

## OpenAguaDSS

OpenAguaDSS is in the beginning stages of development. Documentation forthcoming.

## Hydra web service API

Documentation for Hydra Platform is under development. However, the following seem to be reliable:
* API functions: http://umwrg.github.io/HydraPlatform/devdocs/HydraServer/index.html#api-functions
* Example usage with JSON: http://umwrg.github.io/HydraPlatform/tutorials/plug-in/tutorial_json.html