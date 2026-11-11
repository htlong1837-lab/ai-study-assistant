import test from "node:test";
import assert from "node:assert/strict";
import {findTextInSpans, newEventId, normalizeRect, normalizeText, selectionStartPage} from "../../modules/qa/reader/frontend/reader_logic.mjs";

test("normalizes Vietnamese NFC and whitespace",()=>{
  assert.equal(normalizeText("Tiếng   Việt"),"tiếng việt");
});
test("normalizes page rectangles into 0..1 coordinates",()=>{
  assert.deepEqual(normalizeRect({left:20,top:30,right:60,bottom:50},{left:10,top:10,width:100,height:100},2),{page:2,x:.1,y:.2,w:.4,h:.2});
});
test("uses the first selected rectangle's page for cross-page selections",()=>{
  assert.equal(selectionStartPage([{page:4},{page:5}],1),4);
  assert.equal(selectionStartPage([],3),3);
});
test("finds citation text across multiple PDF text spans",()=>{
  assert.deepEqual(findTextInSpans(["The key", "idea is here"],"key idea"),{start:4,end:12});
  assert.equal(findTextInSpans(["not found"],"missing"),null);
});
test("creates a non-empty event ID",()=>assert.ok(newEventId({}) .length>0));
