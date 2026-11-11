import {api} from '/scripts/api.js';
import {request} from '../shell/client.mjs';
import {syncBranch} from './graph.mjs';

export class StudioJobs extends EventTarget {
  constructor() { super(); this.run=null; this.timer=null; this.disposed=false; this.starting=false; }
  emit(run) { this.run=run; this.dispatchEvent(new CustomEvent('status',{detail:run})); }
  async generate(recipe) {
    if (this.starting) return;
    this.starting=true;
    try {
      const run=await request('prepare',{recipe,request_id:crypto.randomUUID(),client_id:api.clientId});
      this.emit(run); this.poll();
    } finally { this.starting=false; }
  }
  async resume(id) { this.emit(await request('job',undefined,{id})); this.poll(); }
  async poll() {
    clearTimeout(this.timer);
    if (this.disposed || !this.run) return;
    try {
      let run=await request('job',undefined,{id:this.run.id});
      this.emit(run);
      if (run.status==='ready') {
        const workflow=await syncBranch(run.detail.graph,run.recipe.kind,run.recipe);
        run=await request('start',{id:run.id,workflow});
      }
      this.emit(run);
      if (!['completed','failed','canceled','interrupted'].includes(run.status)) this.timer=setTimeout(()=>this.poll(),1000);
    } catch (error) {
      this.dispatchEvent(new CustomEvent('error',{detail:error}));
      if (!this.disposed) this.timer=setTimeout(()=>this.poll(),3000);
    }
  }
  async cancel() { if(this.run) this.emit(await request('cancel',{id:this.run.id})); }
  dispose() { this.disposed=true; clearTimeout(this.timer); }
}
