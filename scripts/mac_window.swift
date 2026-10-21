import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
    var window: NSWindow!
    var web: WKWebView!
    var service: Process?
    var timer: Timer?
    var floating = false
    var regularFrame: NSRect?
    var checking = false
    var loaded = false
    var lastLaunch = Date.distantPast
    let port = Int(ProcessInfo.processInfo.environment["OUTLOOK_ASSISTANT_PORT"] ?? "8484") ?? 8484
    var address: URL {URL(string:"http://localhost:\(port)/")!}

    func applicationDidFinishLaunching(_ notification: Notification) {
        let menu = NSMenu()
        let appMenu = NSMenu()
        let item = NSMenuItem(); item.submenu = appMenu; menu.addItem(item)
        appMenu.addItem(withTitle: "Show Outlook Assistant", action: #selector(showWindow), keyEquivalent: "0").target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Outlook Assistant", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let edit = NSMenu(title: "Edit")
        for (title, action, key) in [("Undo", "undo:", "z"), ("Cut", "cut:", "x"), ("Copy", "copy:", "c"), ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a")] {
            edit.addItem(withTitle: title, action: Selector(action), keyEquivalent: key)
        }
        let editItem=NSMenuItem(title:"Edit",action:nil,keyEquivalent:"");editItem.submenu=edit;menu.addItem(editItem)
        NSApp.mainMenu = menu
        let configuration = WKWebViewConfiguration()
        configuration.userContentController.add(self,name:"saveBackup")
        configuration.userContentController.addUserScript(WKUserScript(source:"window.nativeFilePickerReady=true;", injectionTime:.atDocumentStart, forMainFrameOnly:true))
        web = WKWebView(frame: .zero, configuration: configuration)
        web.navigationDelegate = self; web.uiDelegate = self
        window = NSWindow(contentRect: NSRect(x:0,y:0,width:1240,height:840), styleMask:[.titled,.closable,.miniaturizable,.resizable], backing:.buffered, defer:false)
        window.title = "Outlook Assistant"
        window.minSize = NSSize(width:760,height:600)
        window.contentView = web
        window.isReleasedWhenClosed = false
        window.center(); showWindow()
        web.loadHTMLString("<html><body style='font:17px -apple-system;padding:60px;color:#18366d'><h1>Outlook Assistant</h1><p>Opening your saved workspace…</p></body></html>", baseURL:nil)
        checkService()
        timer = Timer.scheduledTimer(withTimeInterval:3,repeats:true) { [weak self] _ in self?.checkService() }
    }
    @objc func showWindow() { window?.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true) }
    func applicationShouldHandleReopen(_ sender:NSApplication,hasVisibleWindows flag:Bool)->Bool { showWindow();return true }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender:NSApplication)->Bool { false }

    func applicationShouldTerminate(_ sender:NSApplication)->NSApplication.TerminateReply {
        if !loaded {return .terminateNow}
        var answered=false
        let finish: (Bool, String?) -> Void = { saved, message in
            guard !answered else { return }; answered=true
            sender.reply(toApplicationShouldTerminate:saved)
            if !saved {
                self.showWindow()
                let alert=NSAlert();alert.messageText="Your changes haven't finished saving"
                alert.informativeText=message ?? "Keep the app open, check the save status, and try quitting again."
                alert.addButton(withTitle:"Keep app open");alert.beginSheetModal(for:self.window)
            }
        }
        web.callAsyncJavaScript("return await window.flushWorkspace?.();",arguments:[:],in:nil,in:.page) { result in
            switch result {
            case .success(let saved): finish((saved as? Bool) == true,nil)
            case .failure: finish(false,"Check the save status in the app. Your window will stay open so you can retry.")
            }
        }
        DispatchQueue.main.asyncAfter(deadline:.now()+15) {finish(false,"Saving is taking longer than expected. Try again after it finishes.")}
        return .terminateLater
    }
    func userContentController(_ userContentController:WKUserContentController,didReceive message:WKScriptMessage) {
        guard message.name=="saveBackup", message.frameInfo.isMainFrame, message.frameInfo.securityOrigin.host=="localhost", message.frameInfo.securityOrigin.port==port, let body=message.body as? String, body.utf8.count<50_000_000 else{return}
        let panel=NSSavePanel();panel.nameFieldStringValue=body.contains("outlook-task-handoff") ? "Task-handoff.json" : "Outlook-Assistant-Backup.json";panel.canCreateDirectories=true
        panel.beginSheetModal(for:window) { response in
            var saved=false
            if response == .OK, let url=panel.url {do {try body.write(to:url,atomically:true,encoding:.utf8);try FileManager.default.setAttributes([.posixPermissions:0o600],ofItemAtPath:url.path);saved=true}catch{}}
            self.web.evaluateJavaScript("window.nativeBackupDone?.(\(saved ? "true" : "false"));",completionHandler:nil)
        }
    }
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        guard frame.securityOrigin.host == "localhost", frame.securityOrigin.port == port else { completionHandler(nil); return }
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.beginSheetModal(for: window) { result in completionHandler(result == .OK ? panel.urls : nil) }
    }
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = NSAlert(); alert.messageText = message
        alert.addButton(withTitle: "Confirm"); alert.addButton(withTitle: "Cancel")
        alert.beginSheetModal(for: window) { response in completionHandler(response == .alertFirstButtonReturn) }
    }
    func applicationWillTerminate(_ notification:Notification) { timer?.invalidate();if service?.isRunning == true {service?.interrupt()} }
    func checkService() {
        if checking {return};checking=true
        var request=URLRequest(url:address.appendingPathComponent("api/health"));request.timeoutInterval=2
        URLSession.shared.dataTask(with:request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self=self else{return};self.checking=false
                let payload = data.flatMap { try? JSONSerialization.jsonObject(with:$0) as? [String:Any] }
                if payload?["instance"] != nil {
                    if !self.loaded { self.loaded=true;self.web.load(URLRequest(url:self.address)) }
                } else if self.service?.isRunning != true && Date().timeIntervalSince(self.lastLaunch)>10 {
                    self.lastLaunch=Date()
                    let process=Process()
                    process.executableURL=Bundle.main.bundleURL.appendingPathComponent("Contents/MacOS/Outlook Assistant Service")
                    process.arguments=["--port",String(self.port),"--no-browser"]
                    process.standardOutput=FileHandle.nullDevice;process.standardError=FileHandle.nullDevice
                    do { try process.run();self.service=process }
                    catch { self.web.loadHTMLString("<html><body style='font:17px -apple-system;padding:60px'><h1>Could not start the app</h1><p>Your saved data has not been removed. Reinstall the complete Mac app and try again.</p></body></html>",baseURL:nil) }
                }
            }
        }.resume()
    }
    func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!) {

    }
    func webView(_ webView:WKWebView,decidePolicyFor action:WKNavigationAction,decisionHandler:@escaping(WKNavigationActionPolicy)->Void) {
        guard let url=action.request.url else {decisionHandler(.cancel);return}
        if url.scheme == "about" || ((url.host == "localhost" || url.host == "127.0.0.1") && url.port == port && url.scheme == "http") {decisionHandler(.allow);return}
        if action.navigationType == .linkActivated && ["https","http"].contains(url.scheme ?? "") {NSWorkspace.shared.open(url)}
        decisionHandler(.cancel)
    }
    func webView(_ webView:WKWebView,createWebViewWith configuration:WKWebViewConfiguration,for action:WKNavigationAction,windowFeatures:WKWindowFeatures)->WKWebView? {
        if let url=action.request.url, ["https","http"].contains(url.scheme ?? "") {NSWorkspace.shared.open(url)}
        return nil
    }
}
let app=NSApplication.shared
let delegate=AppDelegate()
app.delegate=delegate
app.setActivationPolicy(.regular)
app.run()
