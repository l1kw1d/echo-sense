# Echo Sense

Echo Sense is a generic M2M/sensor platform that runs on Google Cloud Platform, and has 4 primary functions:

* Receiving raw data from distributed devices over the internet (or SMS via a gateway)
* Parsing, analyzing and storing raw data
* Visualizing historical sensor data
* Triggering alarms when rule conditions are met to notify key stakeholders

Echo Sense runs on Google Cloud Platform (App Engine).

Technologies used by Echo Sense include:

* React
* React-Router
* Flux
* Bootstrap and Material UI

Development tools used:

* npm
* Gulp
* Sphinx (for api documentation)

## SETUP

To deploy a new instance of Echo Sense, use the following instructions.

### Setup Obtain Google App Engine SDK

Download the APK from Google.
<https://cloud.google.com/appengine/downloads>

### Create a branch or fork the repo

Using a git client or command line interface, branch or fork this repository into a project directory.

```
git checkout -b <new-branch>
```

Ensure you have npm and gulp installed.
https://www.npmjs.com/package/gulp

In a terminal, visit the project's directory, and run `gulp`. This compiles source files and watches src directories for changes.

### Setup a new Google Cloud project

Visit the Google developer's console: <https://console.developers.google.com/>
Create a new project and choose a unique project ID. You will not need a billing account if usage remains within Google's free tier, which should support low-mid volume use cases.

### Update code configuration

Take the ID from the previous step and update the 'application:' parameter in app.yaml
echo-sense is the project ID for the central Echo Sense project, and needs to be replaced with your new instance's project ID.

Update the APP_OWNER and INSTALL_PW variable in constants.py. Owner should match the Google account you logged into the console with. This will enable the application to send emails.

Update the GA_ID variable in constants.py to enable Google Analytics tracking. Visit Google Analytics to set up a new tracking ID for your project.

### Run the application locally

Open the GoogleAppEngineLauncher application you downloaded with the SDK. In the File menu choose 'Add Existing Application'. Choose the repo's directory as the path. Use a port of your choosing for the dev server. Click the run icon to start the development server.

In a browser, visit http://localhost:[port]
You can find the dev server's admin interface using the admin port specified in the app's settings.

The login page for Echo Sense should appear in the browser.
To speed up creation of your first user account, use the admin install handler: visit http://localhost:PORT/admin/gauth/install.

Fill out all parameters (including the installation password defined in constants.py) to create the initial models needed to login.

This will create the user account. If the email matches the APP_OWNER config variable, the new user will be created as a full admin.

You can now login to Echo Sense on the dev server.

### Deploy to production

Make sure appcfg.py is on your path.

To deploy the application to the production server on Google Cloud Platform, in the command line run the executuable script ./deploy_es.sh.

This script:

1. Runs unit tests in the testing/ directory
2. Runs `gulp production`
3. Deploys files to Google Cloud Platform

Once completed, you should be able to visit http://your-project-id.appspot.com to view the app in production.

You can use the same install handler as used on the dev server to initialize the first user account on production.

http://your-project-id.appspot.com/admin/gauth/install

Routes at /admin/gauth* are protected for admins/owners of the project, so authentication will be required for this step.

### Manage project on Google Cloud Platform

Visit https://console.cloud.google.com. To send emails, you need to authorize all senders, which should match the APP_OWNER you defined in constants.py. This can be done from the App Engine module on GCP, under settings.

### Ready to Go

You are now ready to create additional user accounts, sensor types, and sensors.

1. Create a sensor type and give it a name, and define a JSON schema (see models.py@SensorType)
2. Create a sensor object to match your device's unique ID
3. Point your device to post raw data to the inbox (/<eid>/inbox/<format>/<sensor_kn>), where:

* <eid> is the Enterprise ID (long) (the organizational account that's been created)
* <format> is the short string identifying the format type of incoming data
* <sensor_kn> is the unique identifier (string) for the device

E.g. POST /1234567890/inbox/json/abc-100

# Key Files

## Server Side

* echosense.py -- Creation of the WSGI application and definition of server-side routes
* models.py -- Full data model
* api.py -- All API calls, grouped into classes, mostly named after the model they act on
* cronActions.py -- Handlers for all cron jobs (defined in cron.yaml)
* inbox.py -- Handler for all incoming data from devices, other middle-man servers, etc
* outbox.py -- Handles communication out, mostly for alerting contacts, notifying users, etc
* workers.py -- Defines workers to handle large amounts of data, e.g. the tasks run to process a batch of new records from a sensor
* authorized.py -- Defines a decorator to help with user authentication

## Client Side

* Routes.js -- Definition of client-side (react-router) routes
* App.js -- Main React component for App, which runs for all authenticated users
* components/ -- Directory holding all React components

## Testing

Tests can be run by running the shell script ./run_tests in the root directory. The path to google_appengine may need to be updated.  This script runs all unit tests in the testing/ directory.

# Data Model

The full data model can be found in models.py.

## Important Models

### Sensor

A single sensor measuring one or more values over time.
All sensors must have a sensor type.

'contacts' is a JSON object of with keys of aliases (e.g. 'manager', 'coo'), pointing to values of user IDs. The User() object identified by this ID defines their preferred alert channel (SMS, email, etc). See constants.py@CHANNEL() for options.

### SensorType

Sensor types most importnatly define a schema for the type(s) of data collected.  A schema is defined in JSON, and has 1 or more properties defining the ID or column name for that measured value. Each ID is the key for a child object, which defines the label, unit, and role for this column.

* 'label' (str) - label
* 'unit' (str) - e.g. 'kph'
* 'role' (Array<int>) - see constants.py@COLUMN() roles
* 'calculation' (str, optional)

The schema can include both raw props (values that come direct from sensor) and calculated/processed props that can be populated upon POST, as Record() objects are generated.

*Calculated Columns*

Calculations are string expressions that are parsed by the expression parser, and can include basic arithmetic, equations, and user defined functions. You might, for example, use a calculation to normalize a 3-axis vector to a single magnitude to make it easier to set up a magnitude threshold + alarm.

### Record

This is the primary data point model, and records one or more values (defined by the sensor type's schema) at a specific point in time. Measured values exist as dynamic properties on the model -- read up on GAE's db.Expando for more.

### ProcessTask

Intermittent batch processing task that runs at intervals and can check for rules whose conditions are passed, and optionally store analysis results in an Analysis() object.

To enable processing, you must assign a process task for each sensor you wish to run continuous processing for.  This assignment process creates a SensorProcessTask() object, which is unique for every combination of sensor & process task.

This model holds the state of a particular process task for a particular sensor, including timestamp and status of last run, etc.

Quickly on nomenclature: tasks are GAE objects that run in predefined queues. https://cloud.google.com/appengine/docs/python/taskqueue/ This lets us schedule a task to run in the background at a certain time. ProcessTask() and SensorProcessTask() are Echo Sense models that use GAE tasks for scheduling.

A daily cron job (see 'schedule first processtask' in cron.yaml) runs at end of day to schedule a task to run tomorrow (at time_start), for each processtask that is going to be active.

Tomorrow, when these process tasks run (tasks.py:RunProcessTask), they get a list of all SensorProcessTasks(), one for each sensor that's been assigned this task, and run each. They then create a new GAE task to run after the interval defined in the ProcessTask() object, via the eta parameter.

### SensorProcessTask

Maintains state of a particular process task for a given sensor -- when it was last run, it's last status, etc.

### Rule

Rules are set up to trigger alarms when certain conditions of a sensor are met. The status of each rule linked to a process task is assessed when the process task is run. Rules can have 1-2 values as a threshold or window, and other requirements such as duration or consecutive data points to require before triggering.

Rules can also sleep (be inactive) for specified hours, months, or days (of week or month).

Rules, finally, can identify who to contact when they are triggered.

### Alarm

Alarms are produced when rules are triggered. They define a time window during which the rule was triggering. Alarms produce a historical record of important events (triggered by rules) for a given sensor or target.

# WIP

[![Stories in Ready](https://badge.waffle.io/echomobi/echo-sense.png?label=ready&title=Ready)](http://waffle.io/echomobi/echo-sense)