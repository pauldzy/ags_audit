import sys,os
import httplib, urllib, json
import getpass, time
from time import gmtime, strftime

#------------------------------------------------------------------------------
#
# ArcGIS Services Audit Script
Version = "1.1";
# Last Modified: March 20, 2015
#
# These items may be changed as needed for your environment
# 
# Timeout for calling get token, the default is too long
p_timeout = 15;
#
# Filename for the output report
str_report_file = "ags_report_" + time.strftime("%Y%m%d") + ".txt";
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
   ags_admin    = sys.argv[1];
   ags_password = sys.argv[2];
   ags_server   = sys.argv[3];
   ags_port     = sys.argv[4];

else:
   ags_admin    = raw_input("Enter user name: ");
   ags_password = getpass.getpass("Enter password: ");
   ags_server   = raw_input("Enter server url: ");
   if ags_server[:7] == "http://":
      ags_server = ags_server[7:];
   elif ags_server[:8] == "https://":
      ags_server = ags_server[8:];
   ags_port     = raw_input("Enter port number [6080]: ") or "6080";
   print " "
   
sys.stdout.writer = True;
print "AGS Admin : " + ags_admin
print "AGS Server: " + ags_server + ":" + ags_port
print " "
  
#------------------------------------------------------------------------------
# Step 30
# Fetch token from server
#------------------------------------------------------------------------------
def getToken(username,password,serverName,serverPort,p_timeout):
   # Token URL is typically http://server[:port]/arcgis/admin/generateToken
   tokenURL = "/arcgis/admin/generateToken"
    
   # URL-encode the token parameters:-
   params = urllib.urlencode({
       'username': username
      ,'password': password
      ,'client': 'requestip'
      ,'f': 'json'
   })
    
   headers = {
       "Content-type":"application/x-www-form-urlencoded"
      ,"Accept":"text/plain"
   }
   
   # Connect to URL and post parameters
   try:
      httpConn = httplib.HTTPConnection(serverName,serverPort,timeout=p_timeout)
      httpConn.request("POST",tokenURL,params,headers)
   except Exception as e:
      print "Connecting to " + serverName + ":" + serverPort + " failed when requesting a token."
      print "Please verify the AGS REST API administrative endpoint is accessible at this address."
      print e;
      exit(-100);
   
   # Read response
   response = httpConn.getresponse()
   if (response.status != 200):
      httpConn.close()
      print "Error while fetch tokens from admin URL. Please check the URL and try again."
      return
      
   else:
      data = response.read()
      httpConn.close()
           
      # Extract the token from it
      token = json.loads(data) 
    
      return token['token']

sys.stdout.writer = False;
print "Requesting admin token from " + ags_server + "... (timeout: " + str(p_timeout) + " seconds)";

token = getToken(
    username   = ags_admin
   ,password   = ags_password
   ,serverName = ags_server
   ,serverPort = ags_port
   ,p_timeout  = p_timeout
);

if token == "":
   print "Could not generate a token with the username and password provided."    
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

def fetchJson(ags_server,ags_port,token,serviceURL,addParams=None):
   headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"};
   
   baseParams = {'token': token, 'f': 'json'};
   if addParams is not None:
      baseParams.update(addParams);
   params = urllib.urlencode(baseParams);
   
   httpConn = httplib.HTTPConnection(ags_server, ags_port);
   httpConn.request("POST", serviceURL, params, headers);
   
   response = httpConn.getresponse();
   if (response.status != 200):
      httpConn.close();
      raise NameError("Could not read service info information.");

   data = response.read();
   if not assertJsonSuccess(data):
      raise NameError("Error when reading service information. " + str(data));
   
   dataObj = json.loads(data);
   httpConn.close();

   return dataObj;
   
basics = fetchJson(
    ags_server = ags_server
   ,ags_port   = ags_port
   ,token      = token
   ,serviceURL = "/arcgis/admin/info"
);

print "AGS Version: " + basics["currentversion"] + " Build " + basics["currentbuild"];

#------------------------------------------------------------------------------
# Step 50
# Fetch the machine names 
#------------------------------------------------------------------------------
machines = fetchJson(
    ags_server = ags_server
   ,ags_port   = ags_port
   ,token      = token
   ,serviceURL = "/arcgis/admin/machines"
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
   ,ags_port   = ags_port
   ,token      = token
   ,serviceURL = "/arcgis/admin/services"
);

folders = services["folders"];
rootsrv = services["services"];
     
def service_info(ags_server,ags_port,token,folderName,serviceName,serviceType):

   if folderName is None:
      serviceURL = "/arcgis/admin/services/" + service["serviceName"] + "." + service["type"];
   else:
      serviceURL = "/arcgis/admin/services/" + folder + "/" + child_serv["serviceName"] + "." + child_serv["type"];

   srv_prop = fetchJson(
       ags_server = ags_server
      ,ags_port   = ags_port
      ,token      = token
      ,serviceURL = serviceURL
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
            print "  Cached: " + srv_prop["properties"]["isCached"] + ", " + int_max_record + " max records" 
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
      print "  Schema Locking: " + srv_prop["schemaLockingEnabled"]
         
   try:
      manifest = fetchJson(
          ags_server = ags_server
         ,ags_port   = ags_port
         ,token      = token
         ,serviceURL = serviceURL + "/iteminfo/manifest/manifest.json"
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
      ,ags_port   = ags_port
      ,token      = token
      ,folderName = None
      ,serviceName = service["serviceName"]
      ,serviceType = service["type"]
   );

for folder in folders:
   if folder not in ['System','Utilities']:
      child_services = fetchJson(
          ags_server = ags_server
         ,ags_port   = ags_port
         ,token      = token
         ,serviceURL = "/arcgis/admin/services/" + folder
      );
      for child_serv in child_services["services"]:
      
         print folder
         print child_serv["serviceName"] + " (" + child_serv["type"] + ")"
         
         service_info(
             ags_server  = ags_server
            ,ags_port    = ags_port
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
   ,ags_port   = ags_port
   ,token      = token
   ,serviceURL = "/arcgis/admin/data/findItems"
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
   ,ags_port   = ags_port
   ,token      = token
   ,serviceURL = "/arcgis/admin/data/findItems"
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
    
