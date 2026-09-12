'use strict';
const SQL_JS='https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/';
const MAX_CAPTURE_ROWS=5000;
let SQL=null,db=null,loading=null;

async function ensureSql(){
  if(SQL)return SQL;
  if(!loading){
    importScripts(SQL_JS+'sql-wasm.js');
    loading=initSqlJs({locateFile:f=>SQL_JS+f}).then(x=>SQL=x);
  }
  return loading;
}
function closeDb(){if(db){try{db.close()}catch{}db=null}}
function qIdent(v){return`"${String(v).replace(/"/g,'""')}"`}
function displayCell(v){return v instanceof Uint8Array?`[BLOB ${formatBytes(v.length)}]`:v}
function formatBytes(n){if(n<1024)return`${n} B`;if(n<1048576)return`${(n/1024).toFixed(1)} KB`;return`${(n/1048576).toFixed(1)} MB`}
function schema(){
  if(!db)return[];
  const top=db.exec("SELECT type,name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY type,name")[0]?.values||[];
  return top.map(([type,name])=>({type:String(type),name:String(name),quoted:qIdent(name)}));
}
function isProbablyMutating(sql){
  const s=sql.replace(/^\s*(?:--[^\n]*\n|\/\*[\s\S]*?\*\/\s*)*/,'').toUpperCase();
  return /^(?:INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|VACUUM|REINDEX|ANALYZE|ATTACH|DETACH|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE|PRAGMA\s+(?!TABLE_INFO|INDEX_LIST|INDEX_INFO|DATABASE_LIST|COMPILE_OPTIONS|FOREIGN_KEY_LIST))/i.test(s);
}
function query(sql){
  if(!db)throw new Error('No database is open');
  let stmt;
  try{
    stmt=db.prepare(sql);
    const columns=stmt.getColumnNames().map(String),rows=[];
    let truncated=false;
    if(columns.length){
      while(stmt.step()){
        if(rows.length<MAX_CAPTURE_ROWS)rows.push(stmt.get().map(displayCell));
        else{truncated=true;break}
      }
    }else stmt.step();
    const changed=db.getRowsModified(),mutating=isProbablyMutating(sql)||changed>0;
    const out={columns,rows,truncated,changed,mutating};
    if(mutating){
      const snap=db.export();
      out.snapshot=snap.buffer;
      out.schema=schema();
    }
    return out;
  }finally{if(stmt)try{stmt.free()}catch{}}
}
async function open(bytes){
  const S=await ensureSql();closeDb();db=new S.Database(new Uint8Array(bytes));return{schema:schema()};
}
async function demo(){
  const S=await ensureSql();closeDb();db=new S.Database();
  db.run('CREATE TABLE notes(id INTEGER PRIMARY KEY, title TEXT, category TEXT, score REAL, created_at TEXT);');
  db.run("INSERT INTO notes(title,category,score,created_at) VALUES ('Quiet corners','place',4.8,'2026-01-12'),('A useful shortcut','workflow',4.3,'2026-02-03'),('Morning light','place',4.6,'2026-02-08'),('Tiny rituals','habit',3.9,'2026-03-10'),('One good question','workflow',4.9,'2026-03-17'),('Paper texture','design',4.1,'2026-04-01');");
  const snap=db.export();return{schema:schema(),snapshot:snap.buffer};
}
function exportDb(){if(!db)throw new Error('No database is open');const snap=db.export();return{snapshot:snap.buffer}}

self.onmessage=async e=>{
  const {id,action,payload={}}=e.data||{};
  try{
    let result;
    if(action==='open')result=await open(payload.bytes);
    else if(action==='demo')result=await demo();
    else if(action==='query')result=query(String(payload.sql||''));
    else if(action==='schema')result={schema:schema()};
    else if(action==='export')result=exportDb();
    else throw new Error('Unknown worker action');
    const transfer=[];
    if(result?.snapshot instanceof ArrayBuffer)transfer.push(result.snapshot);
    self.postMessage({id,ok:true,result},transfer);
  }catch(error){self.postMessage({id,ok:false,error:String(error?.message||error)})}
};
