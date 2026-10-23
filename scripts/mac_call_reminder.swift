import Cocoa
import CoreAudio

func appKey(_ bundle: String) -> String? {
    let prefixes=[("com.microsoft.teams2","teams"),("com.microsoft.teams","teams"),("com.tinyspeck.slackmacgap","slack"),("com.google.Chrome","chrome"),("com.apple.Safari","safari"),("com.microsoft.edgemac","edge"),("org.mozilla.firefox","firefox"),("com.brave.Browser","brave"),("us.zoom.xos","zoom")]
    return prefixes.first(where:{bundle == $0.0 || bundle.hasPrefix($0.0+".")})?.1
}

@available(macOS 14.2, *)
func microphoneApps() throws -> [String] {
    var address=AudioObjectPropertyAddress(mSelector:kAudioHardwarePropertyProcessObjectList,mScope:kAudioObjectPropertyScopeGlobal,mElement:kAudioObjectPropertyElementMain)
    var size:UInt32=0
    guard AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject),&address,0,nil,&size)==noErr else {throw NSError(domain:"Audio",code:1)}
    var ids=[AudioObjectID](repeating:0,count:Int(size)/MemoryLayout<AudioObjectID>.size)
    if size==0{return []}
    guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject),&address,0,nil,&size,&ids)==noErr else {throw NSError(domain:"Audio",code:2)}
    var result=Set<String>()
    for id in ids {
        var input:UInt32=0;var inputSize=UInt32(MemoryLayout<UInt32>.size)
        var property=AudioObjectPropertyAddress(mSelector:kAudioProcessPropertyIsRunningInput,mScope:kAudioObjectPropertyScopeGlobal,mElement:kAudioObjectPropertyElementMain)
        guard AudioObjectGetPropertyData(id,&property,0,nil,&inputSize,&input)==noErr,input != 0 else{continue}
        property.mSelector=kAudioProcessPropertyBundleID
        var bundle:Unmanaged<CFString>?;var bundleSize=UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
        guard AudioObjectGetPropertyData(id,&property,0,nil,&bundleSize,&bundle)==noErr,let value=bundle?.takeRetainedValue() else{continue}
        if let key=appKey(value as String){result.insert(key)}
    }
    return result.sorted()
}

struct ReminderLifetime {
    var remaining:TimeInterval=20
    mutating func tick(_ seconds:TimeInterval, interacting:Bool)->Bool {
        if !interacting {remaining=max(0,remaining-seconds)}
        return remaining<=0
    }
}

class Reminder:NSObject,NSApplicationDelegate {
    let base:URL;let instance:String
    var expiryTimer:Timer?;var lifetime=ReminderLifetime();var lastTick=Date()
    var timer:Timer?;var busy=false;var failures=0
    var panel:NSPanel?;var project=NSPopUpButton();var message=NSTextField(labelWithString:"");var record=NSButton();var dismissButton=NSButton();var currentID="";var currentName="";var projectIDs=[String]();var starting=false;var hiddenSince:Date?
    init(base:URL,instance:String){self.base=base;self.instance=instance}
    func request(_ path:String,_ data:[String:Any]?=nil) async throws -> [String:Any] {
        var request=URLRequest(url:base.appendingPathComponent(path));request.timeoutInterval=8
        if let data=data {request.httpMethod="POST";request.setValue("application/json",forHTTPHeaderField:"Content-Type");request.httpBody=try JSONSerialization.data(withJSONObject:data)}
        let (body,response)=try await URLSession.shared.data(for:request)
        let result=(try JSONSerialization.jsonObject(with:body)) as? [String:Any] ?? [:]
        guard (response as? HTTPURLResponse)?.statusCode==200 else{throw NSError(domain:"Reminder",code:1,userInfo:[NSLocalizedDescriptionKey:result["error"] as? String ?? "Could not connect to Outlook Assistant."])}
        return result
    }
    func applicationDidFinishLaunching(_ notification:Notification){poll();timer=Timer.scheduledTimer(withTimeInterval:5,repeats:true){[weak self] _ in self?.poll()}}
    func poll(){
        guard !busy else{return};busy=true
        Task { @MainActor in
            defer{busy=false}
            do {
                let health=try await request("api/health")
                guard health["instance"] as? String==instance else{NSApp.terminate(nil);return}
                let settings=try await request("api/call-prompts")
                var apps=[String]();var probeFailed=false
                if settings["enabled"] as? Bool==true {
                    if #available(macOS 14.2, *) {do{apps=try microphoneApps()}catch{probeFailed=true}}
                }
                let result=try await request("api/call-prompts",["action":"observe","instance":instance,"apps":apps,"error":probeFailed])
                failures=0
                if result["enabled"] as? Bool==false || result["recording"] as? Bool==true {panel?.orderOut(nil);currentID="";return}
                if let ids=result["active_ids"] as? [String],!currentID.isEmpty,!ids.contains(currentID){
                    if hiddenSince==nil{hiddenSince=Date()}
                    if Date().timeIntervalSince(hiddenSince!)>15 && !starting{panel?.orderOut(nil);currentID=""}
                }else{hiddenSince=nil}
                if let candidate=result["candidate"] as? [String:String],currentID.isEmpty,!starting {
                    show(candidate,result["projects"] as? [[String:String]] ?? [])
                    _=try await request("api/call-prompts",["action":"shown","id":currentID])
                }
            }catch{failures+=1;if failures>=3{panel?.orderOut(nil);NSApp.terminate(nil)}}
        }
    }
    @MainActor func show(_ candidate:[String:String],_ projects:[[String:String]]) {
        currentID=candidate["id"] ?? "";currentName=candidate["name"] ?? "An app";hiddenSince=nil
        expiryTimer?.invalidate();lifetime=ReminderLifetime();lastTick=Date()
        let width:CGFloat=360,height:CGFloat=206
        let p=NSPanel(contentRect:NSRect(x:0,y:0,width:width,height:height),styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
        p.level = .floating;p.collectionBehavior=[.canJoinAllSpaces,.fullScreenAuxiliary];p.isFloatingPanel=true;p.hidesOnDeactivate=false;p.isReleasedWhenClosed=false;p.backgroundColor = .clear;p.isOpaque=false;p.hasShadow=true
        let view=NSVisualEffectView(frame:NSRect(x:0,y:0,width:width,height:height));view.material = .popover;view.blendingMode = .behindWindow;view.state = .active;view.wantsLayer=true;view.layer?.cornerRadius=20;view.layer?.masksToBounds=true;p.contentView=view
        let icon=NSImageView(frame:NSRect(x:20,y:142,width:42,height:42));icon.image=NSImage(systemSymbolName:"waveform.circle.fill",accessibilityDescription:nil);icon.contentTintColor = .controlAccentColor;icon.symbolConfiguration=NSImage.SymbolConfiguration(pointSize:36,weight:.medium);view.addSubview(icon)
        let title=NSTextField(labelWithString:"Record this call?");title.font = .systemFont(ofSize:17,weight:.semibold);title.frame=NSRect(x:74,y:164,width:245,height:23);view.addSubview(title)
        message=NSTextField(wrappingLabelWithString:"Microphone in use · \(currentName)");message.font = .systemFont(ofSize:12);message.textColor = .secondaryLabelColor;message.frame=NSRect(x:74,y:132,width:244,height:30);view.addSubview(message)
        dismissButton=NSButton(image:NSImage(systemSymbolName:"xmark",accessibilityDescription:"Dismiss recording reminder")!,target:self,action:#selector(dismiss));dismissButton.isBordered=false;dismissButton.contentTintColor = .secondaryLabelColor;dismissButton.frame=NSRect(x:326,y:172,width:20,height:20);view.addSubview(dismissButton)
        let projectLabel=NSTextField(labelWithString:"Project");projectLabel.font = .systemFont(ofSize:12,weight:.medium);projectLabel.textColor = .secondaryLabelColor;projectLabel.frame=NSRect(x:22,y:102,width:65,height:18);view.addSubview(projectLabel)
        project=NSPopUpButton(frame:NSRect(x:90,y:96,width:250,height:28));projectIDs=[""]+projects.compactMap{$0["id"]};project.addItems(withTitles:["No project"]+projects.map{$0["name"] ?? "Project"});project.setAccessibilityLabel("Save recording to project");project.target=self;project.action=#selector(projectChanged);view.addSubview(project)
        record=NSButton(title:"Record call…",target:self,action:#selector(startRecording));record.bezelStyle = .rounded;record.controlSize = .large;record.bezelColor = .controlAccentColor;record.contentTintColor = .white;record.font = .systemFont(ofSize:13,weight:.semibold);record.frame=NSRect(x:16,y:47,width:328,height:36);view.addSubview(record)
        let disable=NSButton(checkboxWithTitle:"Don’t ask again",target:self,action:#selector(disableReminders));disable.font = .systemFont(ofSize:11);disable.controlSize = .small;disable.frame=NSRect(x:22,y:17,width:170,height:21);view.addSubview(disable)
        let hint=NSTextField(labelWithString:"Closes automatically");hint.font = .systemFont(ofSize:10);hint.textColor = .tertiaryLabelColor;hint.alignment = .right;hint.frame=NSRect(x:194,y:20,width:144,height:15);view.addSubview(hint)
        let screen=NSScreen.main ?? NSScreen.screens.first
        if let frame=screen?.visibleFrame{p.setFrameOrigin(NSPoint(x:frame.maxX-width-20,y:frame.maxY-height-20))}
        panel=p;p.orderFrontRegardless()
        let expiry=Timer(timeInterval:0.25,repeats:true){[weak self] _ in
            guard let self=self else{return}
            Task { @MainActor in
            let now=Date();let elapsed=now.timeIntervalSince(self.lastTick);self.lastTick=now
            let hovered=self.panel?.frame.contains(NSEvent.mouseLocation) ?? false
            if self.lifetime.tick(elapsed,interacting:hovered || self.starting){self.dismiss()}
            }
        }
        expiryTimer=expiry;RunLoop.main.add(expiry,forMode:.common)
    }
    @objc func dismiss(){expiryTimer?.invalidate();expiryTimer=nil;panel?.orderOut(nil);currentID=""}
    @objc func projectChanged(){lifetime=ReminderLifetime();lastTick=Date()}
    @objc func disableReminders(){Task { @MainActor in do{_=try await request("api/call-prompts",["action":"settings","enabled":false]);dismiss()}catch{message.stringValue=error.localizedDescription;lifetime=ReminderLifetime();lastTick=Date()}}}
    @objc func startRecording(){
        guard !starting,project.indexOfSelectedItem>=0,project.indexOfSelectedItem<projectIDs.count else{return}
        starting=true;record.isEnabled=false;dismissButton.isEnabled=false
        let selected=projectIDs[project.indexOfSelectedItem]
        Task { @MainActor in
            defer{starting=false;record.isEnabled=true;dismissButton.isEnabled=true}
            do{_=try await request("api/recorder",["action":"start","project_id":selected,"title":"","video":false,"microphone":true]);dismiss()}
            catch{message.stringValue=error.localizedDescription;lifetime=ReminderLifetime();lastTick=Date()}
        }
    }
}
let args=CommandLine.arguments
if args.contains("--self-test") {
    var lifetime=ReminderLifetime();precondition(!lifetime.tick(19,interacting:false));precondition(!lifetime.tick(60,interacting:true));precondition(lifetime.tick(1,interacting:false))
    lifetime=ReminderLifetime();precondition(!lifetime.tick(0.25,interacting:false))
    assert(appKey("com.microsoft.teams2")=="teams");assert(appKey("com.microsoft.teams2.helper")=="teams");assert(appKey("com.google.Chrome.helper")=="chrome");assert(appKey("com.google.ChromeFake")==nil);assert(appKey("com.brettscharm.outlookassistant.recorder")==nil);print("PASS: supported app attribution and recorder exclusion");exit(0)
}
if args.contains("--probe") {
    if #available(macOS 14.2, *) {do{let apps=try microphoneApps();let data=try JSONSerialization.data(withJSONObject:["supported":true,"apps":apps]);print(String(data:data,encoding:.utf8)!)}catch{print("{\"supported\":true,\"error\":true}");exit(1)}}else{print("{\"supported\":false}")};exit(0)
}
if args.contains("--preview") {
    let app=NSApplication.shared;app.setActivationPolicy(.accessory)
    let preview=Reminder(base:URL(string:"http://127.0.0.1:1")!,instance:"preview")
    Task { @MainActor in preview.show(["id":"preview","name":"Microsoft Teams"],[])}
    DispatchQueue.main.asyncAfter(deadline:.now()+25){NSApp.terminate(nil)}
    app.run();exit(0)
}
guard args.count==3,let url=URL(string:args[1]),url.scheme=="http",url.host=="127.0.0.1",url.port != nil else{exit(2)}
let app=NSApplication.shared;app.setActivationPolicy(.accessory)
let reminder=Reminder(base:url,instance:args[2]);app.delegate=reminder;app.run()
