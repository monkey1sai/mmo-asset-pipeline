const {chromium}=require('C:/Users/IOT/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome',chromiumSandbox:true});
 try{
  const page=await browser.newPage();
  await page.goto('http://127.0.0.1:8774/tools/runtime-qa/three/p4.html?manifest=/runs/qa/ro-swordsman-character-v1/v001/p4/run-07/merged/p4-manifest.json');
  await page.waitForFunction(()=>Boolean(window.cv1p4),null,{timeout:120000});
  const data=await page.evaluate(async()=>{
   const THREE=await import('/tools/runtime-qa/three/node_modules/three/build/three.module.js');
   const {loadModel}=await import('/tools/runtime-qa/three/src/cv1-runtime.js');
   const {prepareAffineFK}=await import('/runs/qa/ro-swordsman-character-v1/continuation-20261007/affine-fk-diagnostic.js');
   const api=window.cv1p4,model=api.model;
   const fresh=await loadModel('/'+api.manifest.clips[api.manifest.base].glb.path,api.manifest.clips[api.manifest.base].fps);
   fresh.root.updateMatrixWorld(true);
   const afk=prepareAffineFK(model,fresh);
   const spec=await(await fetch('/'+api.manifest.transitions.path)).json();
   const local=(side,world)=>{const s=api.manifest.foot_lock.sole_rest_world_blender[side];return new THREE.Vector3(s[0],s[2],-s[1]).applyMatrix4(world.clone().invert());};
   const soleTRS=Object.fromEntries(['L','R'].map(s=>[s,local(s,fresh.bones[`foot.${s}`].matrixWorld)]));
   const soleAffine=Object.fromEntries(['L','R'].map(s=>[s,local(s,afk.restWorld.get(model.bones[`foot.${s}`]))]));
   const rows=[];
   for(const block of api.reference.blocks){
    api.setup(spec.scenarios.find(s=>s.id===block.scenario));api.evaluateAt(block.t,true,false);
    const worlds=afk.evaluate(),joints={},affineJoints={},soles={},affineSoles={};
    for(const side of ['L','R']){
     for(const n of ['upper_leg','lower_leg','foot','toe']){
      const name=`${n}.${side}`,b=model.bones[name];
      joints[name]=new THREE.Vector3().setFromMatrixPosition(b.matrixWorld).toArray();
      affineJoints[name]=new THREE.Vector3().setFromMatrixPosition(worlds.get(b)).toArray();
     }
     soles[side]=soleTRS[side].clone().applyMatrix4(model.bones[`foot.${side}`].matrixWorld).toArray();
     affineSoles[side]=soleAffine[side].clone().applyMatrix4(worlds.get(model.bones[`foot.${side}`])).toArray();
    }
    rows.push({label:block.label,joints,affineJoints,soles,affineSoles});
   }
   return{scope:'diagnostic_only_pre_ik',rows};
  });
  fs.writeFileSync(path.join(__dirname,'runtime-fk.json'),JSON.stringify(data,null,1),{flag:'wx'});
  console.log('FK_DIAGNOSTIC_SAVED '+data.rows.length);
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
