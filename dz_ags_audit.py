import sys,os
import httplib, urllib, urllib2, json, contextlib
import getpass, time
from time import gmtime, strftime

#------------------------------------------------------------------------------
#
# ArcGIS Services Audit Script
Version = "2.0";
# Last Modified: February 16, 2016
#
# These items may be changed as needed for your environment
#
# Filename for the output report
str_report_file = "dz_ags_audit_rpt_" + time.strftime("%Y%m%d") + ".txt";
#
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Step 10
# Set up the report file output
#------------------------------------------------------------------------------
class Reporter(object):
   def __init__(self,file):
      self.filename = file;
      self.terminal = sys.stdout;
      self.file = open(self.filename,"a");
      self.writer = True;
      self.term = True;
      
   def __del__(self):
      sys.stdout = self.terminal;
      self.file.close();      
   
   def write(self,message):
      if self.term:
         self.terminal.write(message);
      if self.writer:
         self.file.write(message);

if os.path.exists(str_report_file):
   os.remove(str_report_file);
   
sys.stdout = Reporter(str_report_file);
  
#------------------------------------------------------------------------------
# Step 20
# Get the server credentials
#------------------------------------------------------------------------------
print " "
print "ArcGIS Services Audit Script";
print "Version " + Version;
print strftime("%Y-%m-%d %H:%M:%S", gmtime());
print " ";

sys.stdout.writer = False;
if len(sys.argv) > 4 and sys.argv[1].find(">") == -1:
   ags_admin     = sys.argv[1];
   ags_password  = sys.argv[2];
   ags_server    = sys.argv[3];
   portal_server = sys.argv[4];
   
else:
   ags_admin     = raw_input("Enter user name: ");
   ags_password  = getpass.getpass("Enter password: ");
   
   ags_server    = raw_input("Enter AGS url: ");
   if ags_server[-1:] == "/":
      ags_server = ags_server[:-1]
      
   portal_server = raw_input(
      "Enter portal url if federated\n   [" + ags_server + "]: "
   ) or ags_server;
   
   if portal_server[-1:] == "/":
      portal_server = portal_server[:-1]
   
   print " "
   
sys.stdout.writer = True;
print "AGS Admin : " + ags_admin;
print "AGS Server: " + ags_server;
print "Portal Server: " + portal_server ;
print " "
  
#------------------------------------------------------------------------------
# Step 30
# Fetch token from server
#------------------------------------------------------------------------------
def submit_request(request):
   """ Returns the response from an HTTP request in json format."""
   with contextlib.closing(urllib2.urlopen(request)) as response:
      job_info = json.load(response)
      return job_info
      
def getPortalToken(username,password,agsUrl,portalUrl):
   """ Returns an authentication token from Portal."""
   
   # Set the username and password parameters before getting the token. 
   params = {
       "username": username
      ,"password": password
      ,"referer" : agsUrl + "/arcgis/rest"
      ,"f"       : "json"
   }
   
   token_url = portalUrl + "/portal/sharing/generateToken";
    
   request = urllib2.Request(token_url,urllib.urlencode(params));
   
   try:   
      token_response = submit_request(request);
   
   except:
      # bounce on hard error once as http may simply die miserably
      token_url = portalUrl.replace("http://", "https://") + "/portal/sharing/generateToken";
      request = urllib2.Request(token_url,urllib.urlencode(params));
      token_response = submit_request(request);
   
   if "token" in token_response:
      token = token_response.get("token")
      return token;
   
   else:
      if "error" in token_response:
         error_mess = token_response.get("error", {}).get("message");
         
         # Request for token must be made through HTTPS.
         if "This request needs to be made over https." in error_mess:
            portal_url = portalUrl.replace("http://", "https://")
            token = get_token(username,password,agsUrl,portal_url)
            return token;
            
         else:
            raise Exception("Error: {} ".format(error_mess))

def getToken(username,password,agsUrl,portalUrl):
   """ Returns an authentication token from AGS."""

   # Set the username and password parameters before getting the token. 
   params = {
       "username": username
      ,"password": password
      ,"referer" : agsUrl + "/arcgis/rest"
      ,"f"       : "json"
   }

   token_url = agsUrl + "/arcgis/tokens/generateToken";
    
   request = urllib2.Request(token_url,urllib.urlencode(params));
    
   token_response = submit_request(request)
    
   if "token" in token_response:
      token = token_response.get("token");
      return token;
   
   else:
      if "error" in token_response:
         error_mess = token_response.get("error", {}).get("message");
         
         # Request for token must be made through HTTPS.
         if "This request needs to be made over https." in error_mess:
            ags_url = agsUrl.replace("http://", "https://")
            token = getToken(username,password,ags_url,portalUrl)
            return token;
         
         elif "You are not authorized to access this information" in error_mess:
            token = getPortalToken(username,password,agsUrl,portalUrl);
            return token;
            
         else:
            raise Exception("Error: {} ".format(error_mess))

sys.stdout.writer = False;
print "Requesting admin token...";

token = getToken(
    username   = ags_admin
   ,password   = ags_password
   ,agsUrl     = ags_server
   ,portalUrl  = portal_server
);
   
if token is None or token == "":
   print "   Error, unable to acquire token."
   exit(-99);     

print "  Success."
print " "
sys.stdout.writer = True;

#------------------------------------------------------------------------------
# Step 40
# Fetch the basics from the server
#------------------------------------------------------------------------------
def assertJsonSuccess(data):
   obj = json.loads(data)
   if 'status' in obj and obj['status'] == "error":
      return False;
   else:
      return True;

def fetchJson(ags_server,token,serviceUrl,addParams=None):
   headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"};
   
   baseParams = {'token': token, 'f': 'json'};
   if addParams is not None:
      baseParams.update(addParams);
   params = urllib.urlencode(baseParams);
   
   req = urllib2.Request(ags_server + serviceUrl,params,headers);
   response = urllib2.urlopen(req)
   
   data = response.read();
   if not assertJsonSuccess(data):
      raise NameError("Error when reading service information. " + str(data));
   
   dataObj = json.loads(data);
   response.close();

   return dataObj;
   
basics = fetchJson(
    ags_server = ags_server
   ,token      = token
   ,serviceUrl = "/arcgis/admin/info"
);

print "AGS Version: " + basics["currentversion"] + " Build " + basics["currentbuild"];

#------------------------------------------------------------------------------
# Step 50
# Fetch the machine names 
#------------------------------------------------------------------------------
machines = fetchJson(
    ags_server = ags_server
   ,token      = token
   ,serviceUrl = "/arcgis/admin/machines"
);

for mach in machines["machines"]:
   print "Machine: " + mach["machineName"];
print "---------------------------------";
print " "

#------------------------------------------------------------------------------
# Step 60
# Dump the remainder to the report only
#------------------------------------------------------------------------------
sys.stdout.writer = False;
print "Now exporting AGS report to " + str_report_file + "...";
sys.stdout.writer = True;
sys.stdout.term = False;
   
#------------------------------------------------------------------------------
# Step 70
# Fetch the root services and child folders
#------------------------------------------------------------------------------
def parseConnection(input):
   csItems = input.split(";")
   output = {}
   for item in csItems:
      (key,value) = item.split("=");
      if key == "USER":
         output["username"] = value;
      if key == "INSTANCE":
         output["instance"] = value;
      if key == "DATABASE":
         output["database"] = value;
   return output;
   
services = fetchJson(
    ags_server = ags_server
   ,token      = token
   ,serviceUrl = "/arcgis/admin/services"
);

folders = services["folders"];
rootsrv = services["services"];
     
def service_info(ags_server,token,folderName,serviceName,serviceType):

   if folderName is None:
      serviceUrl = "/arcgis/admin/services/" + serviceName + "." + serviceType;
      
   else:
      serviceUrl = "/arcgis/admin/services/" + folder + "/" + serviceName + "." + serviceType;

   srv_prop = fetchJson(
       ags_server = ags_server
      ,token      = token
      ,serviceUrl = serviceUrl
   );
   
   if "capabilities" in srv_prop:
      if srv_prop["capabilities"] != "":
         print "  Capabilities: " + srv_prop["capabilities"]
   
   if "properties" in srv_prop:
      if "toolbox" in srv_prop["properties"]: 
         print "  Source: " + srv_prop["properties"]["toolbox"];
         print "  " + srv_prop["properties"]["executionType"] + ", " + srv_prop["properties"]["maximumRecords"] + " max records"
      if "filePath" in srv_prop["properties"]:  
         if not "toolbox" in srv_prop["properties"]: 
            print "  Source: " + srv_prop["properties"]["filePath"];
         
         int_max_record = None;
         if "maximumRecords" in srv_prop["properties"]:
            int_max_record = srv_prop["properties"]["maximumRecords"];
         if "maxRecordCount" in srv_prop["properties"]:   
            int_max_record = srv_prop["properties"]["maxRecordCount"];
         if "isCached" in srv_prop["properties"]:
            print "  Cached: " + srv_prop["properties"]["isCached"] + ", " + str(int_max_record) + " max records" 
         if "minScale" in srv_prop["properties"]:
            print "  Minimum Scale: " + srv_prop["properties"]["minScale"]
      if "enableDynamicLayers" in srv_prop["properties"]:
         print "  Allow modification of order and symbology: " + srv_prop["properties"]["enableDynamicLayers"];
   
   if "extensions" in srv_prop: 
      str_list = "";
      for extension in srv_prop["extensions"]:
         if extension["enabled"] == "true":
            str_list = str_list + extension["typeName"] + ","
      if len(str_list) > 0:
         print "  Extensions: " + str_list[:-1]
   
   if "minInstancesPerNode" in srv_prop:
      print "  Min Instances: " + str(srv_prop["minInstancesPerNode"]) + ", Max Instances: " + str(srv_prop["maxInstancesPerNode"]);
      
   if "schemaLockingEnabled" in srv_prop:
      print "  Schema Locking: " + srv_prop["schemaLockingEnabled"];
      
   # Rather annoyingly, critical image services properties are not exposed in the admin info endpoint
   if serviceType == "ImageServer":
      if folderName is None:
         serviceUrl = "/arcgis/rest/services/" + serviceName + "/" + serviceType;
      
      else:
         serviceUrl = "/arcgis/rest/services/" + folder + "/" + serviceName + "/" + serviceType;
      
      srv_prop = fetchJson(
          ags_server = ags_server
         ,token      = token
         ,serviceUrl = serviceUrl
      );
   
      if "extent" in srv_prop:
         str_extent = "[";
         
         if "xmin" in srv_prop["extent"]:
            str_extent += str(srv_prop["extent"]["xmin"]) + ",";
         else:
            str_extent += "None,";
        
         if "ymin" in srv_prop["extent"]:
            str_extent += str(srv_prop["extent"]["ymin"]) + ",";
         else:
            str_extent += "None,";
            
         if "xmax" in srv_prop["extent"]:
            str_extent += str(srv_prop["extent"]["xmax"]) + ",";
         else:
            str_extent += "None,";
            
         if "ymax" in srv_prop["extent"]:
            str_extent += str(srv_prop["extent"]["ymax"]) + "]";
         else:
            str_extent += "None]";
            
         if "spatialReference" in srv_prop["extent"]:
            str_extent += " wkid: " + str(srv_prop["extent"]["spatialReference"]["wkid"]);
         else:
            str_extent += " wkid: None";
            
         print "  Extent: " + str_extent;
      
      if "pixelSizeX" in srv_prop:
         print "  pixelSizeX: " + str(srv_prop["pixelSizeX"]);
      
      if "pixelSizeY" in srv_prop:
         print "  pixelSizeY: " + str(srv_prop["pixelSizeY"]);
         
      if "bandCount" in srv_prop:
         print "  bandCount: " + str(srv_prop["bandCount"]); 
         
      if "pixelType" in srv_prop:
         print "  pixelType: " + srv_prop["pixelType"]; 
         
      if "serviceDataType" in srv_prop:
         print "  serviceDataType: " + srv_prop["serviceDataType"];
         
      if "defaultMosaicMethod" in srv_prop:
         print "  defaultMosaicMethod: " + srv_prop["defaultMosaicMethod"];
         
      if "hasHistograms" in srv_prop:
         print "  hasHistograms: " + str(srv_prop["hasHistograms"]);
         
      if "hasColormap" in srv_prop:
         print "  hasColormap: " + str(srv_prop["hasColormap"]);
         
      if "spatialReference" in srv_prop:
         print "  spatialReference: " + str(srv_prop["spatialReference"]["wkid"]);   
   
   # Interrogate the manifest for information on data services.  Note the manifest only
   # exists for services created after 10.3 or so.   
   try:
      manifest = fetchJson(
          ags_server = ags_server
         ,token      = token
         ,serviceUrl = serviceUrl + "/iteminfo/manifest/manifest.json"
      );
      
   except:
      manifest = None;
      
   if manifest is None:
      print "  No data sources found.";
   
   elif serviceType == "GPServer":
      print "  Unable to interrogate GPService data sources."
      
   elif "databases" in manifest:
      for db in manifest["databases"]:
         if "onServerConnectionString" in db:
            csItems = parseConnection(db["onServerConnectionString"]);
            if "username" in csItems:
               print "  Database data source:";
               print "    Username: " + csItems["username"];
               print "    Instance: " + csItems["instance"];
            else:
               print "  File data source:";
               print "    Location: " + csItems["database"];
         
         if "datasets" in db:
            if len(db["datasets"]) > 0:
               print "    Datasets:"
               for dataset in db["datasets"]:
                  print "      " + dataset["onServerName"]; 
   
   print " "
        
for service in rootsrv:
   print "<ROOT>"
   print service["serviceName"] + " (" + service["type"] + ")"
  
   service_info(
       ags_server = ags_server
      ,token      = token
      ,folderName = None
      ,serviceName = service["serviceName"]
      ,serviceType = service["type"]
   );

for folder in folders:
   if folder not in ['System','Utilities']:
      child_services = fetchJson(
          ags_server = ags_server
         ,token      = token
         ,serviceUrl = "/arcgis/admin/services/" + folder
      );
      for child_serv in child_services["services"]:
      
         print folder
         print child_serv["serviceName"] + " (" + child_serv["type"] + ")"
         
         service_info(
             ags_server  = ags_server
            ,token       = token
            ,folderName  = folder
            ,serviceName = child_serv["serviceName"]
            ,serviceType = child_serv["type"]
         );

print "---------------------------------";

#------------------------------------------------------------------------------
# Step 80
# Fetch the folder data stores
#------------------------------------------------------------------------------
ds_folders = fetchJson(
    ags_server = ags_server
   ,token      = token
   ,serviceUrl = "/arcgis/admin/data/findItems"
   ,addParams  = {"parentPath":"/fileShares"}
);

for ds in ds_folders["items"]:
   print "Folder Data Store: " + ds["path"].replace("/fileShares/","");
   
   if "clientPath" in ds:
      if ds["clientPath"] is not None:
         print "  Publisher Folder Path:"
         print "    " + ds["clientPath"].replace("\\\\","\\");
      
   print "  Server Folder Path:"
   print "    " + ds["info"]["path"].replace("\\\\","\\");

#------------------------------------------------------------------------------
# Step 90
# Fetch the database data stores
#------------------------------------------------------------------------------
ds_databases = fetchJson(
    ags_server = ags_server
   ,token      = token
   ,serviceUrl = "/arcgis/admin/data/findItems"
   ,addParams  = {"parentPath":"/enterpriseDatabases"}
);

for ds in ds_databases["items"]:
   print "Database Data Store: " + ds["path"].replace("/enterpriseDatabases/","");
   
   if "clientConnectionString" in ds["info"]:
      csItems = parseConnection(ds["info"]["clientConnectionString"])
      print "  Publisher Database Connection:";
      print "    Username: " + csItems["username"];
      print "    Instance: " + csItems["instance"];
      
   if "connectionString" in ds["info"]:
      csItems = parseConnection(ds["info"]["connectionString"])
      print "  Server Database Connection:";
      print "    Username: " + csItems["username"];
      print "    Instance: " + csItems["instance"];

#------------------------------------------------------------------------------
# Step 100
# Finish up and exit
#------------------------------------------------------------------------------
sys.stdout.writer = False;
sys.stdout.term = True;
print "Reporting task complete.";
sys.stdout.writer = True;

print " ";  
print "---------------------------------";
print " ";
