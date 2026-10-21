package main

import "testing"

func TestAllowOnlyCalendarDatabases(t *testing.T) {
	for _, name := range []string{"tokens", "owa-offline-actions", "owa-ai-MAIN_THREAD", "Teams:auth:react-web-client:a:b:c"} {
		if calendarDatabase(name) {
			t.Fatal("unexpected allow", name)
		}
	}
	if !calendarDatabase("owa-offline-data-fixture") {
		t.Fatal("missing new calendar")
	}
}
func TestOutlookAdapter(t *testing.T) {
	o := map[string]any{"Subject": "Fixture", "Start": "2026-10-22T12:00:00.000Z", "End": "2026-10-22T13:00:00.000Z", "CalendarItemType": "Exception", "UID": "fixture-uid", "IsCancelled": false, "IsSeriesCancelled": true, "Body": map[string]any{"Value": "private body"}, "OnlineMeetingJoinUrl": map[string]any{"$undefined": true}, "ItemId": map[string]any{"Id": "fixture-id", "mailboxInfo": map[string]any{"mailboxSmtpAddress": "USER@EXAMPLE.COM"}}, "Organizer": map[string]any{"Mailbox": map[string]any{"Name": "Test person"}}}
	row := outlookRow(o, "fallback")
	if row["subject"] != "Fixture" || row["eventType"] != "Exception" || row["isCancelled"] != true || row["account"] != "user@example.com" || row["objectId"] != "fixture-id" {
		t.Fatal("incorrect normalization")
	}
	if _, ok := row["Body"]; ok {
		t.Fatal("body leaked")
	}
	if _, ok := row["skypeTeamsMeetingUrl"]; ok {
		t.Fatal("undefined field leaked")
	}
}
