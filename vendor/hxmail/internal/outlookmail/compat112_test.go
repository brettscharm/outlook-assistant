package outlookmail
import("encoding/binary";"testing";"github.com/pA1nD/hxmail/internal/hxstore/hxbuild")
func TestOutlook112Header(t *testing.T){
 o:=obj(hxbuild.NewMailHeader(headerSpec())); old:=append([]byte(nil),o.Raw...)
 // 16.112 has an eight-byte shorter fixed region and its trailing string words are eight bytes earlier.
 o.Raw=append(append([]byte(nil),old[:0x428]...),old[0x430:]...);o.Tag=0x428
 for _,off:=range []int{884,900,920,940}{copy(o.Raw[off-8:off],old[off:off+8])}
 h,e:=MapHeader(o);if e!=nil||h.Subject!="Fixture subject"||h.SenderAddress!="sender@example.invalid"||h.Preview!="Fixture preview"{t.Fatalf("wrong 16.112 fields: %+v %v",h,e)}
}
func TestOutlook112Folder(t *testing.T){
 o:=obj(hxbuild.NewMailFolder(hxbuild.MailFolderSpec{Key:5,Parent:3,Name:"Inbox",Type:0x61,Lead:79}));old:=append([]byte(nil),o.Raw...)
 o.Raw=append(append([]byte(nil),old[:0x4c2]...),old[0x4d0:]...);o.Tag=0x4c2
 copy(o.Raw[1076:1084],old[1088:1096]);binary.LittleEndian.PutUint32(o.Raw[1148:],0x61)
 f,e:=MapFolder(o);if e!=nil||f.Name!="Inbox"||f.Kind!="inbox"{t.Fatalf("wrong 16.112 folder: %+v %v",f,e)}
}
func TestOutlook112Body(t *testing.T){
 o:=obj(hxbuild.NewMailBody(hxbuild.MailBodySpec{Key:1,HTML:[]byte("<p>First</p><p>Second</p>"),WordOff:1660,Lead:79}));old:=o.Raw
 o.Raw=append(append([]byte(nil),old[:0x740]...),old[0x74e:]...);o.Tag=0x740
 b:=MapBody(o);if b.State!="inline"||HTMLParagraphs(b.HTML)!="First\n\nSecond"{t.Fatalf("wrong body: %+v",b)}
}
