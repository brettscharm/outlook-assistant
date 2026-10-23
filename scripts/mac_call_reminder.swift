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

class Reminder:NSObject,NSApplicationDelegate {
    let base:URL;let instance:String
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
        let width:CGFloat=360,height:CGFloat=240
        let p=NSPanel(contentRect:NSRect(x:0,y:0,width:width,height:height),styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
        p.level = .floating;p.collectionBehavior=[.canJoinAllSpaces,.fullScreenAuxiliary];p.isFloatingPanel=true;p.hidesOnDeactivate=false;p.isReleasedWhenClosed=false;p.backgroundColor = .windowBackgroundColor;p.hasShadow=true
        let view=NSView(frame:NSRect(x:0,y:0,width:width,height:height));view.wantsLayer=true;view.layer?.cornerRadius=16;view.layer?.masksToBounds=true;p.contentView=view
        let title=NSTextField(labelWithString:"Record this call?");title.font = .systemFont(ofSize:18,weight:.semibold);title.frame=NSRect(x:20,y:196,width:320,height:25);view.addSubview(title)
        message=NSTextField(wrappingLabelWithString:"\(currentName) is using your microphone.\nRecord audio and transcribe the call.");message.textColor = .secondaryLabelColor;message.frame=NSRect(x:20,y:145,width:320,height:42);view.addSubview(message)
        project=NSPopUpButton(frame:NSRect(x:18,y:110,width:324,height:28));projectIDs=[""]+projects.compactMap{$0["id"]};project.addItems(withTitles:["No project"]+projects.map{$0["name"] ?? "Project"});project.setAccessibilityLabel("Save recording to project");view.addSubview(project)
        dismissButton=NSButton(title:"Not now",target:self,action:#selector(dismiss));dismissButton.bezelStyle = .rounded;dismissButton.frame=NSRect(x:20,y:63,width:100,height:32);view.addSubview(dismissButton)
        record=NSButton(title:"Record…",target:self,action:#selector(startRecording));record.bezelStyle = .rounded;record.frame=NSRect(x:226,y:63,width:114,height:32);record.isEnabled = !projectIDs.isEmpty;view.addSubview(record)
        let disable=NSButton(checkboxWithTitle:"Don’t ask to record calls",target:self,action:#selector(disableReminders));disable.frame=NSRect(x:20,y:22,width:310,height:24);view.addSubview(disable)
        let screen=NSScreen.main ?? NSScreen.screens.first
        if let frame=screen?.visibleFrame{p.setFrameOrigin(NSPoint(x:frame.maxX-width-20,y:frame.maxY-height-20))}
        panel=p;p.orderFrontRegardless()
    }
    @objc func dismiss(){panel?.orderOut(nil);currentID=""}
    @objc func disableReminders(){Task { @MainActor in do{_=try await request("api/call-prompts",["action":"settings","enabled":false]);dismiss()}catch{message.stringValue=error.localizedDescription}}}
    @objc func startRecording(){
        guard !starting,project.indexOfSelectedItem>=0,project.indexOfSelectedItem<projectIDs.count else{return}
        starting=true;record.isEnabled=false;dismissButton.isEnabled=false
        let selected=projectIDs[project.indexOfSelectedItem]
        Task { @MainActor in
            defer{starting=false;record.isEnabled=true;dismissButton.isEnabled=true}
            do{_=try await request("api/recorder",["action":"start","project_id":selected,"title":"","video":false,"microphone":true]);dismiss()}
            catch{message.stringValue=error.localizedDescription}
        }
    }
}
let args=CommandLine.arguments
if args.contains("--self-test") {
    assert(appKey("com.microsoft.teams2")=="teams");assert(appKey("com.microsoft.teams2.helper")=="teams");assert(appKey("com.google.Chrome.helper")=="chrome");assert(appKey("com.google.ChromeFake")==nil);assert(appKey("com.brettscharm.outlookassistant.recorder")==nil);print("PASS: supported app attribution and recorder exclusion");exit(0)
}
if args.contains("--probe") {
    if #available(macOS 14.2, *) {do{let apps=try microphoneApps();let data=try JSONSerialization.data(withJSONObject:["supported":true,"apps":apps]);print(String(data:data,encoding:.utf8)!)}catch{print("{\"supported\":true,\"error\":true}");exit(1)}}else{print("{\"supported\":false}")};exit(0)
}
guard args.count==3,let url=URL(string:args[1]),url.scheme=="http",url.host=="127.0.0.1",url.port != nil else{exit(2)}
let app=NSApplication.shared;app.setActivationPolicy(.accessory)
let reminder=Reminder(base:url,instance:args[2]);app.delegate=reminder;app.run()
