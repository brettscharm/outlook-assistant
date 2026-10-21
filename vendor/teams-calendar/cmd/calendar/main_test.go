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

func TestAttendeeAllowlist(t *testing.T) {
	object := map[string]any{"RequiredAttendees": []any{map[string]any{"Mailbox": map[string]any{"Name": "Pat", "EmailAddress": "pat@example.com", "Secret": "hidden"}, "ResponseType": "Accept", "Body": "private"}}, "OptionalAttendees": []any{map[string]any{"Mailbox": map[string]any{"Name": "Sam", "EmailAddress": "sam@example.org"}}}}
	row := outlookRow(object, "account")
	attendees := row["attendees"].([]map[string]any)
	if row["attendeesAvailable"] != true || len(attendees) != 2 || attendees[0]["email"] != "pat@example.com" || attendees[0]["response"] != "Accept" || attendees[1]["type"] != "optional" {
		t.Fatal("attendees lost")
	}
	if _, ok := attendees[0]["Secret"]; ok {
		t.Fatal("unrelated data leaked")
	}
	_, available := attendeeRows(map[string]any{})
	if available {
		t.Fatal("invented coverage")
	}
	_, available = attendeeRows(map[string]any{"RequiredAttendees": []any{}})
	if !available {
		t.Fatal("empty cached list unrecognized")
	}
}
