package outlookmail
import "testing"
func TestParagraphLinks(t *testing.T){
 got:=HTMLParagraphs([]byte(`<p><a href="https://example.com/meet?a=1&amp;b=2">Join meeting</a></p><a href="javascript:alert(1)">Bad</a>`))
 want:="Join meeting (https://example.com/meet?a=1&b=2)\n\nBad"
 if got!=want{t.Fatalf("got %q",got)}
 if HTMLText([]byte(`<a href="https://example.com">Label</a>`))!="Label" {t.Fatal("plain extraction changed")}
}
