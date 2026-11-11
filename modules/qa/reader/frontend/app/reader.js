import * as pdfjs from "../vendor/pdfjs/pdf.mjs";
import {findTextInSpans, newEventId, normalizeRect, normalizeText, selectionStartPage} from "./reader_logic.mjs";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("../vendor/pdfjs/pdf.worker.mjs", import.meta.url).href;
const send = value => window.parent.postMessage({isStreamlitMessage:true,type:"streamlit:setComponentValue",value},"*");
const ready = () => window.parent.postMessage({isStreamlitMessage:true,type:"streamlit:componentReady",apiVersion:1},"*");
const height = () => window.parent.postMessage({isStreamlitMessage:true,type:"streamlit:setFrameHeight",height:document.body.scrollHeight},"*");
const root=document.getElementById("pages"), toolbar=document.getElementById("toolbar");
let args={}, pdf=null, loadingTask=null, renderObserver=null, selectionText="", requestedPdf=false, pdfBytes=null, zoom=1;
const eventId=()=>newEventId();
const pageInput=document.getElementById("pageNumber"),pageCount=document.getElementById("pageCount");
function goToPage(number){
  const total=pdf?.numPages||root.querySelectorAll(".page").length;
  const pageNumber=Math.max(1,Math.min(total,Number(number)||1));pageInput.value=String(pageNumber);
  root.querySelector(`[data-page="${pageNumber}"]`)?.scrollIntoView({behavior:"smooth",block:"start"});
}
document.getElementById("prev").onclick=()=>goToPage(Number(pageInput.value)-1);
document.getElementById("next").onclick=()=>goToPage(Number(pageInput.value)+1);
pageInput.addEventListener("change",()=>goToPage(pageInput.value));
document.getElementById("zoomIn").onclick=()=>{zoom=Math.min(2.5,zoom+.1);if(pdfBytes)renderPdf(pdfBytes).catch(showError)};
document.getElementById("zoomOut").onclick=()=>{zoom=Math.max(.5,zoom-.1);if(pdfBytes)renderPdf(pdfBytes).catch(showError)};
document.getElementById("theme").onclick=()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==="dark"?"light":"dark"};
function selectionRects(sel){
  const out=[];if(!sel||!sel.rangeCount)return out;const range=sel.getRangeAt(0);
  for(const rect of range.getClientRects()){const el=document.elementFromPoint(rect.left+rect.width/2,rect.top+rect.height/2),page=el?.closest(".page");if(!page)continue;const box=page.getBoundingClientRect();out.push(normalizeRect(rect,box,Number(page.dataset.page)))}
  return out;
}

async function renderPdf(bytes){
  if(renderObserver)renderObserver.disconnect();
  if(loadingTask) await loadingTask.destroy().catch(()=>{});
  root.replaceChildren(); pdf=null;
  loadingTask=pdfjs.getDocument({data:bytes,isEvalSupported:false,enableScripting:false,stopAtErrors:false});
  pdf=await loadingTask.promise;
  pageCount.textContent=`/ ${pdf.numPages}`;goToPage(Number(pageInput.value)||1);
  const slots=[];
  const firstPage=await pdf.getPage(1), firstBase=firstPage.getViewport({scale:1});
  const placeholderScale=Math.min(1.5,Math.max(.5,(root.clientWidth-36)/firstBase.width))*zoom;
  const placeholderViewport=firstPage.getViewport({scale:placeholderScale});
  for(let number=1;number<=pdf.numPages;number++){
    const slot=document.createElement("section");slot.className="page";slot.dataset.page=String(number);slot.dataset.ready="false";
    slot.style.width=`${placeholderViewport.width}px`;slot.style.height=`${placeholderViewport.height}px`;root.append(slot);slots.push(slot);
  }
  renderObserver=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){pageInput.value=entry.target.dataset.page;renderPage(Number(entry.target.dataset.page),entry.target).catch(error=>{entry.target.dataset.loading="false";showError(error)})}else releasePage(entry.target)}},{rootMargin:"500px"});
  slots.forEach(slot=>renderObserver.observe(slot)); height();
}

function releasePage(slot){
  if(slot.dataset.loading==="true"||slot.dataset.ready!=="true")return;
  slot.querySelector("canvas")?.remove();slot.querySelector(".textLayer")?.remove();
  slot.dataset.ready="false";
  pdf?.getPage(Number(slot.dataset.page)).then(page=>page.cleanup()).catch(()=>{});
}

async function renderPage(number,slot){
  if(slot.dataset.ready==="true"||slot.dataset.loading==="true")return;
  slot.dataset.loading="true";
  const currentPdf=pdf,page=await currentPdf.getPage(number), base=page.getViewport({scale:1});
  const scale=Math.min(1.5,Math.max(.5,(root.clientWidth-36)/base.width))*zoom;
  const viewport=page.getViewport({scale});
  slot.style.width=`${viewport.width}px`;slot.style.height=`${viewport.height}px`;
  const canvas=document.createElement("canvas"), ratio=Math.min(2,window.devicePixelRatio||1);
  canvas.width=Math.floor(viewport.width*ratio);canvas.height=Math.floor(viewport.height*ratio);
  canvas.style.width=`${viewport.width}px`;canvas.style.height=`${viewport.height}px`;
  slot.append(canvas);
  const ctx=canvas.getContext("2d");await page.render({canvas,canvasContext:ctx,viewport,transform:ratio===1?null:[ratio,0,0,ratio,0,0]}).promise;
  if(pdf!==currentPdf){canvas.remove();slot.dataset.loading="false";return}
  const layer=document.createElement("div");layer.className="textLayer";slot.append(layer);
  const textLayer=new pdfjs.TextLayer({textContentSource:await page.getTextContent(),container:layer,viewport});
  await textLayer.render();slot.dataset.ready="true";slot.dataset.loading="false";paintHighlights(slot);
  const rect=slot.getBoundingClientRect();if(rect.bottom < -500 || rect.top > window.innerHeight+500)releasePage(slot);
}

function renderText(pages){
  if(renderObserver)renderObserver.disconnect();if(loadingTask)loadingTask.destroy().catch(()=>{});pdf=null;pdfBytes=null;
  pageCount.textContent=`/ ${(pages||[]).length}`;root.replaceChildren();for(const page of pages||[]){const article=document.createElement("section");article.className="page text-document";article.dataset.page=String(page.number);article.textContent=page.text||"(Trang không có văn bản)";root.append(article);paintHighlights(article)}height();
}

function paintHighlights(page){
  page.querySelectorAll(".asked-highlight").forEach(el=>el.remove());
  for(const thread of args.highlights||[])for(const rect of thread.rects||[]){if(Number(rect.page)!==Number(page.dataset.page))continue;const mark=document.createElement("button");mark.type="button";mark.className="asked-highlight";mark.setAttribute("aria-label","Mở luồng hỏi về đoạn đã chọn");mark.style.left=`${rect.x*100}%`;mark.style.top=`${rect.y*100}%`;mark.style.width=`${rect.w*100}%`;mark.style.height=`${rect.h*100}%`;mark.onclick=()=>send({event_id:eventId(),type:"open_thread",thread_id:thread.thread_id});page.append(mark)}
}

function showError(error){document.getElementById("error").textContent=String(error?.message||error);}
async function doGoto(go){
  if(!go?.nonce||go.nonce===window.lastGoto)return;window.lastGoto=go.nonce;
  const page=root.querySelector(`[data-page="${Number(go.page)}"]`);if(!page)return;page.scrollIntoView({behavior:"smooth",block:"start"});
  if(pdf&&page.dataset.ready!=="true")await renderPage(Number(go.page),page);
  const needle=normalizeText(go.highlight_text||"");if(!needle)return;
  const spans=[...page.querySelectorAll(".textLayer span")],match=findTextInSpans(spans.map(span=>span.textContent),needle);if(!match)return;
  let offset=0,start=null,end=null;
  for(const span of spans){const node=span.firstChild;if(!node)continue;const length=node.textContent.length;if(start===null&&match.start>=offset&&match.start<=offset+length)start=[node,match.start-offset];if(match.end>=offset&&match.end<=offset+length){end=[node,match.end-offset];break}offset+=length+1}
  if(start&&end){const range=document.createRange();range.setStart(start[0],Math.min(start[1],start[0].length));range.setEnd(end[0],Math.min(end[1],end[0].length));const sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);setTimeout(()=>sel.removeAllRanges(),2500)}
}

function render(next){
  args=next||{};document.getElementById("status").textContent=args.filename||"";document.getElementById("error").textContent="";
  if(args.pdf_b64){window.renderedDoc=args.doc_id;requestedPdf=false;const binary=atob(args.pdf_b64),bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);pdfBytes=bytes;renderPdf(bytes).then(()=>doGoto(args.goto)).catch(showError)}
  else {
    if(args.doc_id!==window.renderedDoc){window.renderedDoc=args.doc_id;if((args.pages||[]).length)renderText(args.pages)}
    if(!pdf&&args.filename?.toLowerCase().endsWith(".pdf")&&!requestedPdf){requestedPdf=true;send({event_id:eventId(),type:"need_pdf",doc_id:args.doc_id})}
    else {root.querySelectorAll(".page").forEach(paintHighlights);doGoto(args.goto)}
  }
}

document.addEventListener("mouseup",()=>{
  const sel=window.getSelection(),text=(sel?.toString()||"").trim(),range=sel?.rangeCount?sel.getRangeAt(0):null,anchor=range?.startContainer?.parentElement,rects=selectionRects(sel);
  const page=anchor?.closest(".page");selectionText=text;
  if(!text||!page||!args.ask_enabled){toolbar.style.display="none";return}
  toolbar.replaceChildren();
  for(const [action,title] of [["explain","Giải thích"],["simplify","Đơn giản hóa"],["translate","Dịch"],["define","Định nghĩa"],["custom","Hỏi…"]]){
    const button=document.createElement("button");button.textContent=title;button.onclick=()=>{let question="";if(action==="custom"){question=window.prompt("Bạn muốn hỏi gì về đoạn đã chọn?")||"";if(!question)return}send({event_id:eventId(),type:"ask",action,page:selectionStartPage(rects,Number(page.dataset.page)),selected_text:selectionText,question,rects});toolbar.style.display="none"};toolbar.append(button)
  }
  toolbar.style.display="block";const bounds=range.getBoundingClientRect();toolbar.style.left=`${Math.max(8,Math.min(window.innerWidth-toolbar.offsetWidth-8,bounds.left))}px`;toolbar.style.top=`${Math.max(8,Math.min(window.innerHeight-toolbar.offsetHeight-8,bounds.bottom+6))}px`;
});
document.addEventListener("keydown",event=>{if(event.key==="Escape")toolbar.style.display="none";if(event.ctrlKey&&event.key==="Enter"&&selectionText&&args.ask_enabled){event.preventDefault();const sel=window.getSelection(),range=sel?.rangeCount?sel.getRangeAt(0):null,rects=selectionRects(sel);send({event_id:eventId(),type:"ask",action:"explain",page:selectionStartPage(rects,Number(range?.startContainer?.parentElement?.closest(".page")?.dataset.page||1)),selected_text:selectionText,rects});toolbar.style.display="none"}});
document.addEventListener("pointerdown",event=>{if(!toolbar.contains(event.target))toolbar.style.display="none"});

window.addEventListener("message",event=>{if(event.source!==window.parent)return;const data=event.data||{};if(data.type==="streamlit:render")render(data.args||{})});
ready();
