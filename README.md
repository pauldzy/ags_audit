# dz_ags_audit
Script to dump the service attributes of ArcGIS Server for comparison or auditing purposes.

As far as I know at the moment (10.3.1) there is no simple way to dump into textual format the service configuration of a given ArcGIS Server.  Why exactly we cannot dump all services and/or critical machine details (such as data stores) to XML or some other text format seems like an oversight to me.

While one administrator having iron-fisted and eagle-eyed control over all AGS servers is ideal, in some development environments various actors with publishing and admin rights may during the course of development or sprints change aspects of services - perhaps to the detriment of others dependent on previous settings.  Oftentimes it may be something as innocent as redeploying a service and failing to enable a WMS for example, other times its could be a bit more nefarious with dev groups making changes to suit their application and thus hosing others.  The point is the poor sap in charge of the server may find this difficult to keep track of and arbitrate.  I felt there was a need to **easily** and **quickly** manually or in automated fashion audit and document the state of a server at any one time. 

The results can then be diffed with previous results to detect changes on a single server or diffed against staging or production to detect new deployments or incompatibilities hidden in services.  For example perhaps the production version of the service has dynamic layers set but the staging service does not.  You want to catch that before the service description file is used to update production.

#### Existing Code
The script in its current stage was banged out rather quickly in 2015 to support a third-party virtualization of my then AGS infrastructure.  I did not spend much time on the output format itself as sorting out the REST calls was work enough.  Ideally the text output of the script and the clunky sysout logging should be replaced perhaps with XML or something else more usable.  However it is functional and a good starting point for anyone interested in creating something more robust.
