
# [Azure Api Spec Monitor][docs]


**Starter Project to monitor changes in Azure Api Spec Repo**

## Dependencies:
* Valid swagger_to_sdk_config.json(https://github.com/Azure/azure-sdk-for-python/blob/master/swagger_to_sdk_config.json) in the zure-sdk-for-python repo
* Working with latest changes commited on Jun 8, 2017
* Sensitive to changes in swagger_to_sdk_config.json structure 

## Features

* Monitors changes 
* Dashboard view 
* To do : link actionable commands via sdkbot  

* Works on Python 2.7 (tbd : test with 3.x)

* Requires environment variables to be set 
* export token=yourgitaccestoken
* export username=basic-flask-authentication-username
* export password=password
