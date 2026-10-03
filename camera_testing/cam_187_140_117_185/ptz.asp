<div class="ptz-name" ng-bind="oLan.ptz"></div>
<div class="ptz-ctrl">
	<div class="ptz-ctrl-l">
		<span class="direction" ng-mousedown="ptzControl(5, oParams.iSpeed)" ng-click="ptzControl(5, 0)"><i class="icon-ptz-left-up"></i></span>
		<span class="direction" ng-mousedown="ptzControl(1, oParams.iSpeed)" ng-click="ptzControl(1, 0)"><i class="icon-ptz-up"></i></span>
		<span class="direction" ng-mousedown="ptzControl(7, oParams.iSpeed)" ng-click="ptzControl(7, 0)"><i class="icon-ptz-right-up"></i></span>
		<span class="direction" ng-mousedown="ptzControl(3, oParams.iSpeed)" ng-click="ptzControl(3, 0)"><i class="icon-ptz-left"></i></span>
		<span class="direction" ng-mousedown="ptzControl(15, oParams.iSpeed)"><i ng-if="oParams.bAuto" class="icon-ptz-auto-sel"></i><i ng-if="!oParams.bAuto" class="icon-ptz-auto"></i></span>
		<span class="direction" ng-mousedown="ptzControl(4, oParams.iSpeed)" ng-click="ptzControl(4, 0)"><i class="icon-ptz-right"></i></span>
		<span class="direction" ng-mousedown="ptzControl(6, oParams.iSpeed)" ng-click="ptzControl(6, 0)"><i class="icon-ptz-left-down"></i></span>
		<span class="direction" ng-mousedown="ptzControl(2, oParams.iSpeed)" ng-click="ptzControl(2, 0)"><i class="icon-ptz-down"></i></span>
		<span class="direction" ng-mousedown="ptzControl(8, oParams.iSpeed)" ng-click="ptzControl(8, 0)"><i class="icon-ptz-right-down"></i></span>
	</div>
	<div class="ptz-ctrl-r">
		<span class="operation">
		    <i class="icon-ptz-zoomout" title="{{oLan.zoom + ' -'}}" ng-mousedown="ptzControl(9, oParams.iSpeed)" ng-click="ptzControl(9, 0)"></i>
		    <i class="icon-ptz-zoomin" title="{{oLan.zoom + ' +'}}" ng-mousedown="ptzControl(10, oParams.iSpeed)" ng-click="ptzControl(10, 0)"></i>
		</span>
		<span class="operation">
            <i class="icon-ptz-focusout" title="{{oLan.focus + ' -'}}" ng-mousedown="ptzControl(11, oParams.iSpeed)" ng-click="ptzControl(11, 0)"></i>
            <i class="icon-ptz-focusin" title="{{oLan.focus + ' +'}}" ng-mousedown="ptzControl(12, oParams.iSpeed)" ng-click="ptzControl(12, 0)"></i>
        </span>
        <span class="operation">
            <i class="icon-ptz-irisout" title="{{oLan.iris + ' -'}}" ng-mousedown="ptzControl(13, oParams.iSpeed)" ng-click="ptzControl(13, 0)"></i>
            <i class="icon-ptz-irisin" title="{{oLan.iris + ' +'}}" ng-mousedown="ptzControl(14, oParams.iSpeed)" ng-click="ptzControl(14, 0)"></i>
        </span>
	</div>
</div>
<div>
	<div slider current-value="oParams.iSpeed" show-box="true" step="1" min="1" max="7"></div>
</div>
<div class="ptz-ctrl-bottom">
    <i ng-class="{'true': 'icon-ptz-light', 'false': 'icon-ptz-light-disabled'}[oPtzCap.bLight]" title="{{oLan.light}}"></i>
    <i ng-class="{'true': 'icon-ptz-wiper', 'false': 'icon-ptz-wiper-disabled'}[oPtzCap.bWiper]" title="{{oLan.wiper}}"></i>
    <i ng-class="{'true': 'icon-ptz-auxfocus', 'false': 'icon-ptz-auxfocus-disabled'}[oPtzCap.bAuxFocus]" title="{{oLan.auxFocus}}" ng-click="setKeyFocus()"></i>
    <i ng-class="{'true': 'icon-ptz-lensinit', 'false': 'icon-ptz-lensinit-disabled'}[oPtzCap.bLensInit]" title="{{oLan.lensInit}}"></i>
    <i ng-class="{'true': 'icon-ptz-menu', 'false': 'icon-ptz-menu-disabled'}[oPtzCap.bMenu]" title="{{oLan.menu}}" ng-click="setMenu()"></i>
    <i ng-class="{'true': 'icon-ptz-manualtrack', 'false': 'icon-ptz-manualtrack-disabled'}[oPtzCap.bManualTack]" title="{{oLan.startManualTrack}}"></i>
    <span ng-if="!oParams.b3DZoom">
        <i ng-class="{'true': 'icon-ptz-zoom3d', 'false': 'icon-ptz-zoom3d-disabled'}[oPtzCap.b3DZoom]" title="{{oLan.start3DZoom}}" ng-click="set3DZoom()"></i>
    </span>
    <span ng-if="oParams.b3DZoom">
        <i class="icon-ptz-zoom3d-on" title="{{oLan.stop3DZoom}}" ng-click="set3DZoom()"></i>
    </span>
</div>
<div id="tabs" class="tabs-2">
	<ul>
		<li><a id="a_tab1" href="#tabs-1" hidefocus></a></li>
		<li><a ng-show="oPtzCap.bSupportPatrols" id="a_tab2" href="#tabs-2" hidefocus></a></li>
        <li><a ng-show="oPtzCap.bSupportPattern" id="a_tab3" href="#tabs-3" hidefocus></a></li>
	</ul>
	<div id="tabs-1">
        <div ng-class="{true:'line-select', false:'line-normal'}[oParams.iPresetIndex===$index]" ng-click="selectPreset($index);" ng-repeat="Preset in oPtzCap.aPresetList">
            <span class="line-name" title="{{Preset.name}}">{{Preset.name}}</span>
            <i ng-show="oParams.iPresetIndex===$index" class="preset-edit boundary" ng-click="setPreset($index+1)" title="{{oLan.set}}"></i>
            <i ng-show="oParams.iPresetIndex===$index" class="preset-goto" ng-click="gotoPreset($index+1)" title="{{oLan.excutePreset}}"></i>
        </div>
	</div>
	<div id="tabs-2">
	    <div ng-show="!oParams.bPatrolEdit" ng-class="{true:'line-select', false:'line-normal'}[oParams.iPatrolIndex===$index]" ng-click="selectPatrol($index);" ng-repeat="Patrol in oPtzCap.aPatrolList">
            <span class="line-name" title="{{Patrol.name}}">{{Patrol.name}}</span>
            <i ng-show="oParams.iPatrolIndex===$index" class="patrol-delete" ng-click="deletePatrol($index+1)" title="{{oLan.delete}}"></i>
            <i ng-show="oParams.iPatrolIndex===$index" class="patrol-edit" ng-click="editPatrol($index+1)" title="{{oLan.set}}"></i>
            <i ng-show="oParams.iPatrolIndex===$index" class="patrol-stop" ng-click="stopPatrol($index+1)" title="{{oLan.stop}}"></i>
            <i ng-show="oParams.iPatrolIndex===$index" class="patrol-start" ng-click="startPatrol($index+1)" title="{{oLan.start}}"></i>
        </div>
        <div ng-show="oParams.bPatrolEdit">
            <div class="patrol-title patrol-title-color">
                <span class="inline-block margin-left10 ellipsis width80" ng-bind="oPtzCap.aPatrolList[oParams.iPatrolIndex].name" title="{{oPtzCap.aPatrolList[oParams.iPatrolIndex].name}}"></span>
                <i class="patrol-preset-up" ng-click="upPatrolPreset()" title="{{oLan.moveUp}}"></i>
                <i class="patrol-preset-down" ng-click="downPatrolPreset()" title="{{oLan.moveDown}}"></i>
                <i class="patrol-preset-delete" ng-click="deletePatrolPreset()" title="{{oLan.delete}}"></i>
                <i class="patrol-preset-add" ng-click="addPatrolPreset()" title="{{oLan.add}}"></i>
            </div>
            <div class="patrol-title">
                <span class="patrol-preset ellipsis" ng-bind="oLan.preset" title="{{oLan.preset}}"></span>
                <span class="patrol-speed ellipsis" ng-bind="oLan.patrolSpeed" title="{{oLan.patrolSpeed}}"></span>
                <span class="patrol-time ellipsis" ng-bind="oLan.time" title="{{oLan.time}}"></span>
                <span class="patrol-time-unit">(s)</span>
            </div>
            <div ng-style="{'width': '100%', 'overflow-y': 'auto', 'height': iPatrolPresetHeight}" class="patrol-bottom-border">
                <div ng-class="{true:'line-select', false:'line-normal'}[oParams.iPatrolPresetIndex===$index]" ng-click="selectPatrolPreset($index)" ng-repeat="PatrolPresets in oParams.aPatrolPreset">
                    <span class="left">
                        <input type="text" class="patrol-text" ng-if="oParams.iPatrolPresetIndex!==$index" ng-model="PatrolPresets.szPresetId"></input>
                        <select class="patrol-select" ng-if="oParams.iPatrolPresetIndex===$index" ng-model="PatrolPresets.szPresetId" ng-options="Preset.szId as Preset.szId for Preset in oPtzCap.aPresetList"></select>
                    </span>
                    <span class="left">
                        <input type="text" class="patrol-text" ng-model="PatrolPresets.szSpeed" ng-keyup="verifySpeedAndTime(0, $index)" />
                    </span>
                    <span class="left">
                        <input type="text" class="patrol-text" ng-model="PatrolPresets.szTime" ng-keyup="verifySpeedAndTime(1, $index)" />
                    </span>
                </div>
            </div>
            <div class="patrol-bottom">
                <span class="patrol-confirm" ng-click="confirmPatrol()" ng-bind="oLan.ok"></span>
                <span class="patrol-cancel" ng-click="cancelPatrol()" ng-bind="oLan.cancel"></span>
            </div>
        </div>
	</div>
	<div id="tabs-3">
        <div ng-class="{true:'line-select', false:'line-normal'}[oParams.iPatternIndex===$index]" ng-click="selectPattern($index);" ng-repeat="pattern in oPtzCap.aPatternList">
            <span class="line-name">{{pattern.name}}</span>
            <i ng-show="oParams.iPatternIndex===$index" class="track-delete" ng-click="deletePattern($index+1)" title="{{oLan.delete}}"></i>
            <i ng-show="oParams.iPatternIndex===$index" class="track-stop-record" ng-click="stopRecord($index+1)" title="{{oLan.stopRecording}}"></i>
            <i ng-show="oParams.iPatternIndex===$index" class="track-record" ng-click="startRecord($index+1)" title="{{oLan.startRecording}}"></i>
            <i ng-show="oParams.iPatternIndex===$index" class="track-stop" ng-click="stopPattern($index+1)" title="{{oLan.stop}}"></i>
            <i ng-show="oParams.iPatternIndex===$index" class="track-start" ng-click="startPattern($index+1)" title="{{oLan.start}}"></i>
        </div>
	</div>
</div>