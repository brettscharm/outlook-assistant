// Read calendar records only, from legacy Teams and the embedded Outlook calendar.
package main

import (
	"context"
	"encoding/json"
	"github.com/ourostack/m365crawl/internal/indexeddb"
	"github.com/ourostack/m365crawl/internal/teamsdesktop"
	"github.com/ourostack/m365crawl/internal/v8"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func calendarDatabase(name string) bool {
	if strings.HasPrefix(name, "owa-offline-data-") {
		return true
	}
	manager, _, ok := teamsdesktop.ParseDatabaseName(name)
	return ok && manager == "calendar" && !teamsdesktop.Denied(name)
}
func nested(object map[string]any, keys ...string) any {
	var value any = object
	for _, key := range keys {
		m, ok := value.(map[string]any)
		if !ok {
			return nil
		}
		value = m[key]
	}
	return value
}
func outlookRow(object map[string]any, account string) map[string]any {
	row := map[string]any{"account": account, "source": "Teams calendar"}
	for source, target := range map[string]string{"Subject": "subject", "Start": "startTime", "End": "endTime", "CalendarItemType": "eventType", "IsCancelled": "isCancelled", "IsAllDayEvent": "isAllDayEvent", "Location": "location", "OnlineMeetingJoinUrl": "skypeTeamsMeetingUrl", "LastModifiedTime": "lastModifiedTime", "UID": "iCalUID", "ResponseType": "responseType", "IsDraft": "isDraft"} {
		value := object[source]
		switch value.(type) {
		case string, bool:
			row[target] = value
		}
	}
	row["objectId"] = nested(object, "ItemId", "Id")
	row["organizerName"] = nested(object, "Organizer", "Mailbox", "Name")
	if mailbox, ok := nested(object, "ItemId", "mailboxInfo", "mailboxSmtpAddress").(string); ok && mailbox != "" {
		row["account"] = strings.ToLower(mailbox)
	}
	if object["IsSeriesCancelled"] == true {
		row["isCancelled"] = true
	}
	return row
}
func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	rows := []map[string]any{}
	skipped := 0
	readSources := 0
	root := teamsdesktop.DefaultRoot()
	sources, _, _ := teamsdesktop.Discover(root)
	// New Teams embeds Outlook in partitioned Chromium storage. Inspect database
	// metadata, then allow only owa-offline-data-* / events, never messages or auth.
	paths, _ := filepath.Glob(filepath.Join(root, "*", "WebStorage", "*", "IndexedDB", "indexeddb.leveldb"))
	for _, path := range paths {
		sources = append(sources, teamsdesktop.Source{LevelDBDir: path, BlobDir: filepath.Join(filepath.Dir(path), "indexeddb.blob")})
	}
	for _, source := range sources {
		func() {
			folder, clean, e := teamsdesktop.Snapshot(ctx, source)
			if e != nil {
				skipped++
				return
			}
			defer clean()
			db, e := indexeddb.OpenWith(filepath.Join(folder, "leveldb"), filepath.Join(folder, "blob"), indexeddb.OpenOptions{KeepDatabase: calendarDatabase})
			if e != nil {
				skipped++
				return
			}
			defer db.Close()
			databases, e := db.Databases()
			if e != nil {
				skipped++
				return
			}
			hasCalendar := false
			for _, database := range databases {
				modern := strings.HasPrefix(database.Name, "owa-offline-data-")
				manager, account, ok := teamsdesktop.ParseDatabaseName(database.Name)
				if !modern && (!ok || manager != "calendar") {
					continue
				}
				for _, store := range database.Stores {
					if (modern && store.Name != "events") || (!modern && store.Name != "calendar") {
						continue
					}
					hasCalendar = true
					e = db.Records(database.ID, store.ID, func(record indexeddb.Record) error {
						if ctx.Err() != nil {
							return ctx.Err()
						}
						if len(rows) >= 50000 {
							skipped++
							return nil
						}
						value, e := db.Decode(database.ID, record.Raw)
						if e != nil {
							skipped++
							return nil
						}
						raw, e := v8.Canonical(value)
						if e != nil {
							skipped++
							return nil
						}
						raw, _ = teamsdesktop.Scrub(raw)
						var object map[string]any
						if json.Unmarshal(raw, &object) != nil {
							skipped++
							return nil
						}
						if modern {
							rows = append(rows, outlookRow(object, database.Name))
							return nil
						}
						row := map[string]any{"account": account.TenantID + "/" + account.UserID, "source": "Legacy Teams calendar"}
						for _, key := range []string{"objectId", "iCalUID", "subject", "startTime", "endTime", "eventType", "isCancelled", "isAllDayEvent", "organizerName", "location", "skypeTeamsMeetingUrl", "lastModifiedTime"} {
							if v, ok := object[key]; ok {
								row[key] = v
							}
						}
						rows = append(rows, row)
						return nil
					})
					if e != nil {
						skipped++
					}
				}
			}
			if hasCalendar {
				readSources++
			}
		}()
	}
	json.NewEncoder(os.Stdout).Encode(map[string]any{"events": rows, "skipped": skipped, "sources": readSources})
}
