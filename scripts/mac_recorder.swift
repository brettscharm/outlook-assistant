import Cocoa
import AVFoundation
import ScreenCaptureKit

// Match Retina pixels without upscaling; bound memory and encoder load on large displays.
struct RecordingVideoSize {
    let width: Int
    let height: Int
    var bitRate: Int { min(24_000_000, max(6_000_000, width * height * 3)) }
    static func fit(width: Double, height: Double, scale: Double) -> RecordingVideoSize {
        guard width.isFinite, height.isFinite, scale.isFinite, width > 0, height > 0, scale > 0 else {
            return RecordingVideoSize(width:1920,height:1080)
        }
        let w=width*scale, h=height*scale
        let ratio=min(1, 3840/max(w,h), sqrt(8_294_400/(w*h)))
        return RecordingVideoSize(width:max(2,Int(w*ratio/2)*2),height:max(2,Int(h*ratio/2)*2))
    }
}

// Independent, visible recorder. No background capture begins until the system picker returns a selection.
@available(macOS 14.0, *)
final class Recorder: NSObject, NSApplicationDelegate, SCContentSharingPickerObserver, SCStreamOutput, SCStreamDelegate, AVCaptureAudioDataOutputSampleBufferDelegate {
    let directory: URL
    let video: Bool
    let microphone: Bool
    let queue = DispatchQueue(label: "outlook.recorder.samples")
    var stream: SCStream?
    var mic: AVCaptureSession?
    var writer: AVAssetWriter?
    var screenInput: AVAssetWriterInput?
    var audioInput: AVAssetWriterInput?
    var micInput: AVAssetWriterInput?
    var began = false
    var firstTime = CMTime.invalid
    var stopping = false
    var started: Date?
    var state = "choosing"
    var message = "Choose a screen or app to record."
    var window: NSWindow!
    var label: NSTextField!
    var statusItem: NSStatusItem!
    var timer: Timer?
    var activity: NSObjectProtocol?
    var sampleError: String?
    var completionNote = ""
    var exported = false
    var videoSize = RecordingVideoSize(width:1920,height:1080)
    init(directory: URL, video: Bool, microphone: Bool) { self.directory=directory;self.video=video;self.microphone=microphone }
    func report(_ state: String, _ message: String) {
        self.state=state;self.message=message
        label?.stringValue=message
        if state=="saving"{statusItem?.button?.title="Saving recording…"}
        let status: [String:Any] = ["state":state,"message":message,"heartbeat":Date().timeIntervalSince1970,"started_at":started?.timeIntervalSince1970 ?? 0,"pid":ProcessInfo.processInfo.processIdentifier]
        if let data=try? JSONSerialization.data(withJSONObject:status) {try? data.write(to:directory.appendingPathComponent("status.json"),options:.atomic)}
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        window=NSWindow(contentRect:NSRect(x:0,y:0,width:420,height:155),styleMask:[.titled,.miniaturizable],backing:.buffered,defer:false)
        window.title="Outlook Assistant Recorder";window.isReleasedWhenClosed=false
        label=NSTextField(wrappingLabelWithString:message);label.frame=NSRect(x:24,y:70,width:372,height:60)
        let stop=NSButton(title:"Stop recording",target:self,action:#selector(stopPressed));stop.frame=NSRect(x:230,y:20,width:165,height:32)
        window.contentView?.addSubview(label);window.contentView?.addSubview(stop);window.center();window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
        statusItem=NSStatusBar.system.statusItem(withLength:NSStatusItem.variableLength);statusItem.button?.title="○ Recorder"
        let menu=NSMenu();menu.addItem(withTitle:"Show recorder",action:#selector(showRecorder),keyEquivalent:"").target=self;menu.addItem(withTitle:"Stop and save",action:#selector(stopPressed),keyEquivalent:"").target=self;statusItem.menu=menu
        report("choosing","Choose a screen or app. Only audio is saved unless screen video was selected.")
        timer=Timer.scheduledTimer(withTimeInterval:1,repeats:true){[weak self] _ in self?.tick()}
        let picker=SCContentSharingPicker.shared
        var config=SCContentSharingPickerConfiguration();config.allowedPickerModes=[.singleDisplay,.singleApplication,.singleWindow];config.allowsChangingSelectedContent=false
        picker.defaultConfiguration=config;picker.add(self);picker.isActive=true;picker.present()
    }
    @objc func showRecorder(){window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)}
    func tick(){
        if FileManager.default.fileExists(atPath:directory.appendingPathComponent("stop").path){stopPressed();return}
        if state=="recording",let started=started {
            let elapsed=Int(Date().timeIntervalSince(started));statusItem.button?.title=String(format:"● REC %02d:%02d",elapsed/60,elapsed%60)
            let size=((try? FileManager.default.attributesOfItem(atPath:directory.appendingPathComponent("capture.mov").path)[.size]) as? NSNumber)?.int64Value ?? 0
            let free=((try? FileManager.default.attributesOfFileSystem(forPath:directory.path)[.systemFreeSize]) as? NSNumber)?.int64Value ?? 0
            if elapsed>=10800 || size>=2_000_000_000 || free<size+750_000_000 {completionNote = elapsed>=10800 ? " Stopped at the three-hour limit." : size>=2_000_000_000 ? " Stopped at the size limit." : " Stopped because disk space is low.";stopPressed();return}
        }
        report(state,message)
    }
    func contentSharingPicker(_ picker: SCContentSharingPicker, didCancelFor stream: SCStream?){if self.stream==nil{finish("cancelled","Recording cancelled.")}}
    func contentSharingPickerStartDidFailWithError(_ error: Error){finish("failed",error.localizedDescription)}
    func contentSharingPicker(_ picker: SCContentSharingPicker, didUpdateWith filter: SCContentFilter, for stream: SCStream?){
        guard self.stream==nil,!stopping else{return}
        report("starting","Starting recording…")
        Task { @MainActor in
            if microphone {
                let allowed=await AVCaptureDevice.requestAccess(for:.audio)
                if !allowed {finish("failed","Microphone access was denied. Enable it in System Settings or turn off microphone recording.");return}
            }
            do {try await start(filter)}catch{finish("failed",error.localizedDescription)}
        }
    }
    func prepareWriter() throws -> AVAssetWriter {
        let output=try AVAssetWriter(outputURL:directory.appendingPathComponent("capture.mov"),fileType:.mov)
        func audioTrack()->AVAssetWriterInput {let track=AVAssetWriterInput(mediaType:.audio,outputSettings:[AVFormatIDKey:kAudioFormatMPEG4AAC,AVSampleRateKey:48000,AVNumberOfChannelsKey:2,AVEncoderBitRateKey:128000]);track.expectsMediaDataInRealTime=true;output.add(track);return track}
        audioInput=audioTrack();if microphone{micInput=audioTrack()}
        if video {let track=AVAssetWriterInput(mediaType:.video,outputSettings:[AVVideoCodecKey:AVVideoCodecType.h264,AVVideoWidthKey:videoSize.width,AVVideoHeightKey:videoSize.height,AVVideoCompressionPropertiesKey:[AVVideoAverageBitRateKey:videoSize.bitRate,AVVideoExpectedSourceFrameRateKey:30,AVVideoMaxKeyFrameIntervalKey:60,AVVideoProfileLevelKey:AVVideoProfileLevelH264HighAutoLevel]]);track.expectsMediaDataInRealTime=true;output.add(track);screenInput=track}
        writer=output
        return output
    }
    func start(_ filter: SCContentFilter) async throws {
        guard !stopping else{return}
        videoSize=RecordingVideoSize.fit(width:Double(filter.contentRect.width),height:Double(filter.contentRect.height),scale:Double(filter.pointPixelScale))
        let config=SCStreamConfiguration();config.width=video ? videoSize.width : 1280;config.height=video ? videoSize.height : 720;config.scalesToFit=true;config.minimumFrameInterval=CMTime(value:1,timescale:30);config.queueDepth=4;config.capturesAudio=true;config.sampleRate=48000;config.channelCount=2;config.excludesCurrentProcessAudio=true;config.showsCursor=true
        let output=try prepareWriter()
        let capture=SCStream(filter:filter,configuration:config,delegate:self);self.stream=capture
        try capture.addStreamOutput(self,type:.audio,sampleHandlerQueue:queue)
        if video {try capture.addStreamOutput(self,type:.screen,sampleHandlerQueue:queue)}
        if microphone {
            let session=AVCaptureSession()
            guard let device=AVCaptureDevice.default(for:.audio) else {throw NSError(domain:"Recorder",code:1,userInfo:[NSLocalizedDescriptionKey:"No microphone is available."])}
            let input=try AVCaptureDeviceInput(device:device),sink=AVCaptureAudioDataOutput()
            guard session.canAddInput(input),session.canAddOutput(sink) else {throw NSError(domain:"Recorder",code:2,userInfo:[NSLocalizedDescriptionKey:"The microphone could not be opened."])}
            session.addInput(input);session.addOutput(sink);sink.setSampleBufferDelegate(self,queue:queue);mic=session
        }
        guard output.startWriting() else {throw output.error ?? NSError(domain:"Recorder",code:3)}
        try await capture.startCapture()
        mic?.startRunning();started=Date();activity=ProcessInfo.processInfo.beginActivity(options:[.userInitiated,.idleSystemSleepDisabled],reason:"Recording a call")
        report("recording",video ? "Recording screen (\(videoSize.width) × \(videoSize.height)), call audio\(microphone ? " and microphone" : ""). Use Stop to save." : "Recording call audio\(microphone ? " and microphone" : ""). No screen video is saved.")
    }
    func append(_ sample: CMSampleBuffer,to input: AVAssetWriterInput?){
        guard let writer=writer,let input=input,!stopping,CMSampleBufferDataIsReady(sample) else{return}
        if !began {firstTime=CMSampleBufferGetPresentationTimeStamp(sample);writer.startSession(atSourceTime:firstTime);began=true}
        if CMTimeCompare(CMSampleBufferGetPresentationTimeStamp(sample),firstTime)<0{return}
        if writer.status == .writing,input.isReadyForMoreMediaData,!input.append(sample){sampleError=writer.error?.localizedDescription ?? "A recording sample could not be saved.";DispatchQueue.main.async{self.stopPressed()}}
    }
    func stream(_ stream: SCStream,didOutputSampleBuffer sampleBuffer:CMSampleBuffer,of type:SCStreamOutputType){
        if type == .screen {
            guard let attachments=CMSampleBufferGetSampleAttachmentsArray(sampleBuffer,createIfNecessary:false) as? [[SCStreamFrameInfo:Any]],let raw=attachments.first?[.status] as? Int,SCFrameStatus(rawValue:raw) == .complete else{return}
            append(sampleBuffer,to:screenInput)
        } else if type == .audio {append(sampleBuffer,to:audioInput)}
    }
    func captureOutput(_ output:AVCaptureOutput,didOutput sampleBuffer:CMSampleBuffer,from connection:AVCaptureConnection){append(sampleBuffer,to:micInput)}
    func stream(_ stream:SCStream,didStopWithError error:Error){DispatchQueue.main.async{self.sampleError=error.localizedDescription;self.stopPressed()}}
    @objc func stopPressed(){
        guard !stopping else{return};stopping=true
        guard let stream=stream else{finish("cancelled","Recording cancelled.");return}
        report("saving","Saving recording. Keep the recorder open…")
        Task { @MainActor in
            try? await stream.stopCapture();mic?.stopRunning()
            queue.async { [self] in
                guard let writer=writer,began else{DispatchQueue.main.async{self.finish("failed","No audio or video was captured.")};return}
                screenInput?.markAsFinished();audioInput?.markAsFinished();micInput?.markAsFinished()
                writer.finishWriting {DispatchQueue.main.async{self.exportRecording()}}
            }
        }
    }
    func exportRecording(){
        guard writer?.status == .completed else{finish("failed",writer?.error?.localizedDescription ?? "Recording could not be finalized. The partial file was retained.");return}
        let asset=AVURLAsset(url:directory.appendingPathComponent("capture.mov"))
        guard let exporter=AVAssetExportSession(asset:asset,presetName:video ? AVAssetExportPresetHighestQuality : AVAssetExportPresetAppleM4A) else{finish("failed","Could not prepare the recording. The original file was retained.");return}
        Task { @MainActor in
        let tracks: [AVAssetTrack]
        do {tracks=try await asset.loadTracks(withMediaType:.audio)}catch{finish("failed",error.localizedDescription);return}
        let mix=AVMutableAudioMix();mix.inputParameters=tracks.map{track in let p=AVMutableAudioMixInputParameters(track:track);p.setVolume(1,at:.zero);return p};exporter.audioMix=mix
        exporter.outputURL=directory.appendingPathComponent(video ? "recording.mp4" : "recording.m4a");exporter.outputFileType=video ? .mp4 : .m4a
        await exporter.export()
        if exporter.status == .completed {
            if video {
                do {
                    let saved=AVURLAsset(url:exporter.outputURL!)
                    guard let track=try await saved.loadTracks(withMediaType:.video).first else {throw NSError(domain:"Recorder",code:4,userInfo:[NSLocalizedDescriptionKey:"Export did not contain screen video. The original file was retained."])}
                    let size=try await track.load(.naturalSize)
                    guard Int(size.width)==videoSize.width,Int(size.height)==videoSize.height else {throw NSError(domain:"Recorder",code:5,userInfo:[NSLocalizedDescriptionKey:"Export changed the video resolution. The original file was retained."])}
                }catch {self.finish("failed",error.localizedDescription);return}
            }
            self.exported=true;try? FileManager.default.removeItem(at:self.directory.appendingPathComponent("capture.mov"));self.finish("complete",self.sampleError == nil ? "Recording saved."+self.completionNote : "Recording saved after capture stopped: "+self.sampleError!)}
        else {self.finish("failed",exporter.error?.localizedDescription ?? "Export failed. The original recording was retained.")}
        }
    }
    // Exercises the real writer/mixer with generated tones, never opens capture devices.
    func selfTest() async {
        do {
            if video {videoSize=RecordingVideoSize.fit(width:1512,height:982,scale:2)}
            let format=AVAudioFormat(standardFormatWithSampleRate:48000,channels:2)!
            let buffer=AVAudioPCMBuffer(pcmFormat:format,frameCapacity:48000)!;buffer.frameLength=48000
            for channel in 0..<2 {for frame in 0..<48000 {buffer.floatChannelData![channel][frame]=Float(sin(Double(frame)*2*Double.pi*440/48000)*0.15)}}
            let wav=directory.appendingPathComponent("tone.wav")
            do {let file=try AVAudioFile(forWriting:wav,settings:format.settings);try file.write(from:buffer)}
            let asset=AVURLAsset(url:wav);let track=try await asset.loadTracks(withMediaType:.audio)[0]
            let reader=try AVAssetReader(asset:asset),output=AVAssetReaderTrackOutput(track:track,outputSettings:[AVFormatIDKey:kAudioFormatLinearPCM]);reader.add(output)
            let writer=try prepareWriter();guard writer.startWriting(),reader.startReading() else{throw NSError(domain:"SelfTest",code:1)}
            while let sample=output.copyNextSampleBuffer(){
                while !(audioInput!.isReadyForMoreMediaData && micInput!.isReadyForMoreMediaData) {try await Task.sleep(nanoseconds:1_000_000)}
                append(sample,to:audioInput);append(sample,to:micInput)
            }
            if video {
                for frame in 0..<15 {
                    var pixel: CVPixelBuffer?
                    CVPixelBufferCreate(kCFAllocatorDefault,videoSize.width,videoSize.height,kCVPixelFormatType_32BGRA,nil,&pixel)
                    guard let pixel=pixel else{throw NSError(domain:"SelfTest",code:2)}
                    CVPixelBufferLockBaseAddress(pixel,[]);memset(CVPixelBufferGetBaseAddress(pixel),48,CVPixelBufferGetDataSize(pixel));CVPixelBufferUnlockBaseAddress(pixel,[])
                    var format:CMVideoFormatDescription?;CMVideoFormatDescriptionCreateForImageBuffer(allocator:kCFAllocatorDefault,imageBuffer:pixel,formatDescriptionOut:&format)
                    var timing=CMSampleTimingInfo(duration:CMTime(value:1,timescale:15),presentationTimeStamp:CMTime(value:Int64(frame),timescale:15),decodeTimeStamp:.invalid),sample:CMSampleBuffer?
                    CMSampleBufferCreateReadyWithImageBuffer(allocator:kCFAllocatorDefault,imageBuffer:pixel,formatDescription:format!,sampleTiming:&timing,sampleBufferOut:&sample)
                    while !screenInput!.isReadyForMoreMediaData{try await Task.sleep(nanoseconds:1_000_000)}
                    append(sample!,to:screenInput)
                }
                screenInput?.markAsFinished()
            }
            audioInput?.markAsFinished();micInput?.markAsFinished();await writer.finishWriting();exportRecording()
        }catch{finish("failed",error.localizedDescription)}
    }
    func finish(_ state:String,_ message:String){
        stopping=true;timer?.invalidate();SCContentSharingPicker.shared.isActive=false
        if let activity=activity{ProcessInfo.processInfo.endActivity(activity)}
        report(state,message);DispatchQueue.main.asyncAfter(deadline:.now()+0.3){NSApp.terminate(nil)}
    }
    func applicationShouldTerminate(_ sender:NSApplication)->NSApplication.TerminateReply {if !["complete","failed","cancelled"].contains(state){stopPressed();return .terminateCancel};return .terminateNow}
}
let arguments=CommandLine.arguments
if arguments.contains("--self-test-dimensions") {
    let cases:[(Double,Double,Double,Int,Int)]=[(1512,982,2,3024,1964),(1920,1080,1,1920,1080),(2560,1440,2,3840,2160),(1080,1920,2,2160,3840),(800,600,1,800,600),(1001,701,1,1000,700),(0,0,1,1920,1080)]
    for (w,h,s,ew,eh) in cases {let result=RecordingVideoSize.fit(width:w,height:h,scale:s);precondition(result.width==ew && result.height==eh)}
    print("Video dimensions passed");exit(0)
}
if arguments.contains("--check") {print("Outlook Recorder 1; macOS 14+; audio and optional screen video");exit(0)}
guard arguments.count==4 || arguments.count==3 && arguments[1].hasPrefix("--self-test") else{exit(2)}
if #available(macOS 14.0, *) {
    let app=NSApplication.shared;app.setActivationPolicy(.accessory)
    if arguments[1].hasPrefix("--self-test") {
        let recorder=Recorder(directory:URL(fileURLWithPath:arguments[2],isDirectory:true),video:arguments[1]=="--self-test-video",microphone:true)
        Task { @MainActor in await recorder.selfTest() };app.run()
    } else {
        let recorder=Recorder(directory:URL(fileURLWithPath:arguments[1],isDirectory:true),video:arguments[2]=="video",microphone:arguments[3]=="mic")
        app.delegate=recorder;app.run()
    }
} else {exit(3)}
