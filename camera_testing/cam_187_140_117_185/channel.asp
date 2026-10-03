<div class="device">
	<div class="device-icon"></div>
	<div class="device-name ellipsis" title="{{szDeviceName}}"><label ng-bind="szDeviceName"></label></div>
</div>
<div class="channel-list">
	<div class="ch" ng-repeat="ch in aChlist">
		<div class="ch-btns">
		    <div ng-show="bSyncPlayStatus" class="ch-check"><input type="checkbox" class="checkbox" ng-disabled="bSyncPlay" ng-click="checkChannel($event.target, $index)" /></div>
			<div ng-show="!bSyncPlayStatus" ng-class="{true:'ch-btn playing', false:'ch-btn play'}[ch.bPlay]" ng-click="play($index)"></div>
		</div>
		<div ng-if="bPreview" class="ch-name ellipsis" channel="{{ch.iId}}" ng-click="select($event.target, $index)" ng-dblclick="play($index)" title="{{ch.szName}}">{{ch.szName}}</div>
		<div ng-if="!bPreview" class="ch-name ellipsis" channel="{{ch.iId}}" ng-click="select($event.target, $index)" title="{{ch.szName}}">{{ch.szName}}</div>
		<div class="ch-btns recordContainer">
			<div ng-show="bPreview && !bFirefoxNoPlugin && bSupportRecord" ng-class="{true:'ch-btn recording', false:'ch-btn record'}[ch.bRecord]" ng-click="record($index)"></div>
		</div>
		<div ng-if="bPreview && ch.szType!='zero'" class="ch-btns" stream stream-type="ch.iStreamType" lan="oLan" num="iStreamNum" on-change="changeStream" channel-index="{{$index}}"></div>
	</div>
</div>