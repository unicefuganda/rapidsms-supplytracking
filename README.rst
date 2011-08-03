SupplyTracking
==============
SupplyTracking is a simple supplies tracking application / tool designed to track goods in transit from the time they leave a ware house to the time they are signed off by a consignee as received. SupplyTracking allows dispatchers of goods to know which consignements are in transit at any one point, which ones have been received by consignees and the state of the consignements, ie damaged or complete. SupplyTracking also helps consignees know which consignements are enroute to them. Consignements are tracked by means of a unique waybill number tagged on each pacel dispatched.

SupplyTracking is done by way of SMS and the application itself is dependent on RapidSMS (www.rapidsms.org).

Technically speaking, SupplyTracking leverage the work of rapidsms-script (github.com/daveycrockett/rapidsms-script/) to provide an easy system for automated conversation-like communication between the SupplyTracking application, dispatchers of goods, transporters and consignees.

A running example of supplytracking can be viewed at status160.rapidsms.org/supplytracking/

Requirements
============
 - Currently, SupplyTracking can be installed as a modular part of any RapidSMS installation, but work is underway to make an easy_install setup installation for it as an independent application.
 - Python 2.6 (www.python.org/download/) : On linux machines, you can usually use your system's package manager to perform the installation
 - MySQL or PostgreSQL are recommended
 - Script (https://github.com/daveycrockett/rapidsms-script)
 - Xlrd - a python excel manipulation module
 - Some sort of SMS Connectivity, via an HTTP gateway. It is assumed here that the RapidSMS instance referred to in bullet 1 above already has SMS Connectivity. See http://docs.rapidsms.org for more information on how to configure a GSM modem or other SMS connectivity mechanisms available for RapidSMS.

Installation
============
To install SupplyTracking, you need Git.
 - Within your RapidSMS project folder, clone a copy of the supplyTracking code as follows:

	~/Projects/rapidsms_proj$ git clone git@github.com:asseym/rapidsms-supplytracking.git
	~/Projects/rapidsms_proj$ pip install xlrd

Configuration
=============
 - Add supplytracking to your INSTALLED_APPS in your RapidSMS settings file, and setup the url for the supplytracking application as well.
 - Add supplytracking to your SMS_APPS in your RapidSMS settings file
 - Visit http://your-rapid-sms-installation/<supplytracking-url>, you should see the supplytracking index view
 - Upload a list of consignees, transporters and the deliveries. See Microsoft excel templates for these lists, they are bundled with the supplytracking application (look in supplytracking/fixtures).

