<div class="logo"></div>
<ul id="nav" class="nav">
	<li ng-show="bSptCmPreview"><a ng-bind="oLan.preview" ng-click="jumpTo('preview')"></a></li>
	<li ng-show="bSptCmRecord"><a ng-bind="oLan.playback" ng-click="jumpTo('playback')"></a></li>
	<li ng-show="bSupportPicSearch"><a ng-bind="oLan.picture" ng-click="jumpTo('download')"></a></li>
	<li ng-show="bSupportApplication"><a ng-bind="oLan.application" ng-click="jumpTo('application')"></a></li>
	<li><a ng-bind="oLan.config" ng-click="jumpTo('config')"></a></li>
</ul>
<div class="header-r">
	<div class="user">
		<div class="icon"></div>
		<label ng-bind="username"></label>
	</div>
	<div class="help" ng-show="bSupportHelp" ng-click="help()">
		<div class="icon"></div>
    	<label class="pointer" ng-bind="oLan.help"></label>
	</div>
	<div class="exit" ng-click="exit()" >
		<div class="icon"></div>
        <label class="pointer" ng-bind="oLan.logout"></label>
	</div>
</div>