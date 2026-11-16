const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const base=require('node:path').join(__dirname,'../dist');const ctx={window:{}};vm.createContext(ctx);
for(const name of ['data.js','thresholds.js'])vm.runInContext(fs.readFileSync(`${base}/${name}`,'utf8'),ctx);
const D=ctx.window.VFRS_DATA,summarize=ctx.window.VFRS_THRESHOLDS.summarize;
for(const station of ['all',...D.stations.map(s=>String(s.id))])for(const year of ['all','2023','2024','2025']){
 const result=summarize(D.incidents,station,year);
 assert.equal(result.total,D.scopes[`${station}|${year}`].Annual[0].responses);
 assert.equal(result.within4+result.between4and6+result.above6,result.total);
 assert(result.within4<=result.within6&&result.within6<=result.total);
}
const sample=[{year:2025,responses:[["a",1,0,0],["b",1,0,240],["c",1,0,241],["d",1,0,360],["e",1,0,361],["f",1,1,120],["g",null,0,120],["h",1,0,null]]}];
const edge=summarize(sample,'1','2025');assert.equal(edge.total,5);assert.equal(edge.within4,2);assert.equal(edge.within6,4);assert.equal(edge.above6,1);
assert.equal(summarize(sample,'2','2025').rate4,null);
console.log('Verified all 44 station/year denominators; inclusive thresholds, zero values, cancelled/unmapped exclusions, empty selections and band totals.');
console.log(JSON.stringify(summarize(D.incidents)));
