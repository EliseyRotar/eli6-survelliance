<!doctype html>
<html>
<head>
	<title></title>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
	<meta http-equiv="X-UA-Compatible" content="IE=edge" >
	<meta http-equiv="Pragma" content="no-cache" />
	<meta http-equiv="Cache-Control" content="no-cache, must-revalidate" />
	<meta http-equiv="Expires" content="0" />
	<script>
		document.write("<link type='text/css' href='../ui/css/ui.css?version=" + new Date().getTime() + "' rel='stylesheet' />");
	</script>
</head>
<body class="preview">
<div class="layout-north" id="header" ng-controller="headerController">
	<div class="header" ng-include="'common/header.asp'" onload="headerLoaded()"></div>
</div>
<div class="layout-west" id="channel" ng-controller="channelController">
	<div class="channel" ng-include="'common/channel.asp'" onload="channelLoaded()"></div>
</div>
<div class="layout-center">
	<div class="layout-center-inner" id="plugin" ng-controller="pluginController">
		<div class="plugin" ng-include="'common/plugin.asp'" onload="pluginLoaded()"></div>
	</div>
	<div class="layout-south-inner" id="tool" ng-controller="toolController">
		<div class="tool" ng-include="'common/tool.asp'"  onload="toolLoaded()"></div>
	</div>
</div>
<div class="layout-east" id="ptz" ng-controller="ptzController">
	<div class="ptz" ng-include="'common/ptz.asp'" onload="ptzLoaded()"></div>
</div>
<div class="layout-south">
	<div class="footer" id="footer"></div>
</div>
</body>
<script id="seajsnode" src="../script/lib/seajs/seajs/sea.min.js"></script>
<script>
	document.write("<script src='../script/lib/seajs/config/sea-config.js?version=" + new Date().getTime() + "' ></scr" + "ipt>");
</script>
<script for=PreviewActiveX event="GetSelectWndInfo(SelectWndInfo)">
	GetSelectWndInfo(SelectWndInfo);
</script>
<script for=PreviewActiveX event="PluginEventHandler(iEventType, iParam1, iParam2)">
    PluginEventHandler(iEventType, iParam1, iParam2);
</script>
<script for=PreviewActiveX event="ZoomInfoCallback(szZoomInfo)">
	ZoomInfoCallback(szZoomInfo);
</script>
<script for=PreviewActiveX event="SetZeroChanEnlarge(EnlargeInfo)">
	SetZeroChanEnlarge(EnlargeInfo);
</script>
<script for=PreviewActiveX event="MouseEvent(szXml)">
	MouseEvent(szXml);
</script>
<script for=PreviewActiveX event="KeyBoardEvent(szXml)">
	KeyBoardEvent(szXml);
</script>
</html>