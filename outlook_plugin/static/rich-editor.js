/* Only a small inert email-formatting vocabulary is allowed into the editor. */
function cleanEmailHTML(source){
 const parsed=new DOMParser().parseFromString(String(source),'text/html');
 const output=document.createElement('div');
 const tags=new Set('P DIV BR SPAN B STRONG I EM U S STRIKE UL OL LI BLOCKQUOTE A FONT H1 H2 H3 HR TABLE TBODY TR TD TH'.split(' '));
 const styles=['color','background-color','font-family','font-size','font-weight','font-style','text-decoration','text-align','margin-left'];
 function walk(node,parent){
  if(node.nodeType===3){parent.append(document.createTextNode(node.textContent));return;}
  if(node.nodeType!==1||['SCRIPT','STYLE','IFRAME','OBJECT','SVG','MATH','IMG'].includes(node.tagName))return;
  if(!tags.has(node.tagName)){for(const child of node.childNodes)walk(child,parent);return;}
  const el=document.createElement(node.tagName.toLowerCase());
  for(const prop of styles){const value=node.style.getPropertyValue(prop);if(value&&!/url\s*\(|expression|var\(/i.test(value))el.style.setProperty(prop,value);}
  if(node.tagName==='A'){const href=node.getAttribute('href')||'';if(/^(https?:\/\/|mailto:)/i.test(href)){el.setAttribute('href',href);el.setAttribute('rel','noopener noreferrer');}}
  if(node.tagName==='FONT')for(const name of ['face','size','color']){const value=node.getAttribute(name);if(value)el.setAttribute(name,value);}
  for(const child of node.childNodes)walk(child,el);parent.append(el);
 }
 for(const child of parsed.body.childNodes)walk(child,output);return output.innerHTML;
}
async function copyRichDraft(plain,html){
 if(html&&window.ClipboardItem&&navigator.clipboard?.write){await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([cleanEmailHTML(html)],{type:'text/html'}),'text/plain':new Blob([plain],{type:'text/plain'})})]);return;}
 await navigator.clipboard.writeText(plain);if(html)notice('Copied plain text. To preserve formatting, select the draft and press ⌘C.');
}
function richEditor(plain,html,onChange){
 const wrapper=document.createElement('div');wrapper.className='rich-composer';
 const toolbar=document.createElement('div');toolbar.className='rich-toolbar';toolbar.setAttribute('role','group');toolbar.setAttribute('aria-label','Email formatting');
 const box=document.createElement('div');box.className='rich-body';box.contentEditable='true';box.setAttribute('role','textbox');box.setAttribute('aria-multiline','true');box.setAttribute('aria-label','Draft reply');
 if(html)box.innerHTML=cleanEmailHTML(html);else box.textContent=plain;
 let range=null;
 const remember=()=>{const selection=window.getSelection();if(selection.rangeCount&&box.contains(selection.anchorNode)&&box.contains(selection.focusNode))range=selection.getRangeAt(0).cloneRange();};
 box.addEventListener('keyup',remember);box.addEventListener('mouseup',remember);box.addEventListener('input',()=>{remember();onChange();});
 const run=(command,value)=>{box.focus();if(range&&box.contains(range.commonAncestorContainer)){const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);}document.execCommand(command,false,value);remember();onChange();};
 const button=(label,command,value)=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.title=label;b.onmousedown=e=>e.preventDefault();b.onclick=()=>run(command,value);toolbar.append(b);return b;};
 for(const [label,command] of [['Bold','bold'],['Italic','italic'],['Underline','underline'],['Strikethrough','strikeThrough'],['Bullets','insertUnorderedList'],['Numbering','insertOrderedList'],['Align left','justifyLeft'],['Center','justifyCenter'],['Align right','justifyRight'],['Indent','indent'],['Outdent','outdent'],['Clear formatting','removeFormat'],['Undo','undo'],['Redo','redo']])button(label,command);
 function select(label,options,command){const control=document.createElement('select');control.setAttribute('aria-label',label);const initial=new Option(label,'');control.append(initial);for(const [name,value] of options)control.append(new Option(name,value));control.onchange=()=>{if(control.value)run(command,control.value);control.value='';};toolbar.append(control);}
 select('Font',['Arial','Calibri','Helvetica','Verdana','Georgia','Times New Roman','Courier New'].map(x=>[x,x]),'fontName');
 select('Font size',[['Small','2'],['Normal','3'],['Large','4'],['Extra large','5'],['Heading','6'],['Huge','7']],'fontSize');
 for(const [label,command,value] of [['Text color','foreColor','#202124'],['Highlight','hiliteColor','#ffff00']]){const holder=document.createElement('label');holder.textContent=label;const input=document.createElement('input');input.type='color';input.value=value;input.setAttribute('aria-label',label);input.oninput=()=>run(command,input.value);holder.append(input);toolbar.append(holder);}
 const link=document.createElement('input');link.type='url';link.placeholder='https://…';link.setAttribute('aria-label','Link URL');toolbar.append(link);const add=button('Insert link','createLink');add.onclick=()=>{if(!/^(https?:\/\/|mailto:)/i.test(link.value)){notice('Enter a full https:// or mailto: link.');return;}run('createLink',link.value);link.value='';};button('Remove link','unlink');
 box.addEventListener('paste',event=>{event.preventDefault();const data=event.clipboardData;run(data.getData('text/html')?'insertHTML':'insertText',data.getData('text/html')?cleanEmailHTML(data.getData('text/html')):data.getData('text/plain'));});
 box.addEventListener('drop',event=>event.preventDefault());
 box.addEventListener('click',event=>{if(event.target.closest('a'))event.preventDefault();});
 wrapper.append(toolbar,box);return {wrapper,box,setHTML(value){box.innerHTML=cleanEmailHTML(value);range=null;}};
}
