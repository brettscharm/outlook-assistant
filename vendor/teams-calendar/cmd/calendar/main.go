// Calendar-only adapter. Never emit unrelated stores or raw decode diagnostics.
package main
import("context";"encoding/json";"os";"path/filepath";"time";"github.com/ourostack/m365crawl/internal/teamsdesktop";"github.com/ourostack/m365crawl/internal/indexeddb";"github.com/ourostack/m365crawl/internal/v8")
func main(){
 ctx,cancel:=context.WithTimeout(context.Background(),90*time.Second);defer cancel()
 rows:=[]map[string]any{};skipped:=0
 sources,_,err:=teamsdesktop.Discover(teamsdesktop.DefaultRoot());if err!=nil{os.Exit(2)}
 for _,source:=range sources {func(){
  folder,clean,e:=teamsdesktop.Snapshot(ctx,source);if e!=nil{skipped++;return};defer clean()
  db,e:=indexeddb.OpenWith(filepath.Join(folder,"leveldb"),filepath.Join(folder,"blob"),indexeddb.OpenOptions{KeepDatabase:func(name string)bool{manager,_,ok:=teamsdesktop.ParseDatabaseName(name);return ok&&manager=="calendar"&&!teamsdesktop.Denied(name)}});if e!=nil{skipped++;return};defer db.Close()
  databases,e:=db.Databases();if e!=nil{skipped++;return}
  for _,database:=range databases{manager,account,ok:=teamsdesktop.ParseDatabaseName(database.Name);if !ok||manager!="calendar"{continue}
   for _,store:=range database.Stores{if store.Name!="calendar"{continue}
    e=db.Records(database.ID,store.ID,func(record indexeddb.Record)error{
     if ctx.Err()!=nil{return ctx.Err()};if len(rows)>=50000{skipped++;return nil}
     value,e:=db.Decode(database.ID,record.Raw);if e!=nil{skipped++;return nil};raw,e:=v8.Canonical(value);if e!=nil{skipped++;return nil};raw,_=teamsdesktop.Scrub(raw)
     var object map[string]any;if json.Unmarshal(raw,&object)!=nil{skipped++;return nil}
     row:=map[string]any{"account":account.TenantID+"/"+account.UserID}
     for _,key:=range []string{"objectId","iCalUID","subject","startTime","endTime","eventType","isCancelled","isAllDayEvent","organizerName","location","skypeTeamsMeetingUrl","lastModifiedTime"}{if v,ok:=object[key];ok{row[key]=v}}
     rows=append(rows,row);return nil
    });if e!=nil{skipped++}
   }
  }
 }()}
 json.NewEncoder(os.Stdout).Encode(map[string]any{"events":rows,"skipped":skipped,"sources":len(sources)})
}
