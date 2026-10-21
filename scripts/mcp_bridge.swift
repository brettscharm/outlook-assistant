// Local stdio bridge: no model calls, no file access, no listening socket.
import Foundation
let port = Int(ProcessInfo.processInfo.environment["OUTLOOK_ASSISTANT_PORT"] ?? "8484") ?? 8484
while let line=readLine() {
    guard let data=line.data(using:.utf8) else {continue}
    guard let parsed=try? JSONSerialization.jsonObject(with:data) else {
        print("{\"jsonrpc\":\"2.0\",\"id\":null,\"error\":{\"code\":-32700,\"message\":\"Parse error\"}}");fflush(stdout);continue
    }
    guard parsed is [String:Any] else {
        print("{\"jsonrpc\":\"2.0\",\"id\":null,\"error\":{\"code\":-32600,\"message\":\"Invalid request\"}}");fflush(stdout);continue
    }
    var result:Data?
    let semaphore=DispatchSemaphore(value:0)
    var request=URLRequest(url:URL(string:"http://127.0.0.1:\(port)/api/mcp")!)
    request.httpMethod="POST";request.httpBody=data;request.timeoutInterval=60
    request.setValue("application/json",forHTTPHeaderField:"Content-Type")
    URLSession.shared.dataTask(with:request) { data,response,error in
        if let http=response as? HTTPURLResponse,http.statusCode==200 {result=data}
        semaphore.signal()
    }.resume()
    semaphore.wait()
    if let bytes=result,let value=try? JSONSerialization.jsonObject(with:bytes),!(value is NSNull),let clean=try? JSONSerialization.data(withJSONObject:value,options:[.sortedKeys]),let output=String(data:clean,encoding:.utf8) {print(output)}
    else if result == nil {
        let req=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any]
        if let id=req?["id"],let bytes=try? JSONSerialization.data(withJSONObject:["jsonrpc":"2.0","id":id,"error":["code":-32000,"message":"Open Outlook Assistant on this Mac, then retry."]]),let output=String(data:bytes,encoding:.utf8) {print(output)}
    }
    fflush(stdout)
}
