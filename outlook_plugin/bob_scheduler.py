"""Shared bounded Bob queue; no spending limits and no unbounded process spawning."""
import os
import subprocess
import threading
import time
from contextlib import contextmanager


def machine_capacity():
    cores=os.cpu_count() or 2
    try:
        ram=int(subprocess.check_output(['/usr/sbin/sysctl','-n','hw.memsize'],timeout=2,text=True,stderr=subprocess.DEVNULL))
    except (OSError,ValueError,subprocess.SubprocessError):ram=8*1024**3
    gb=ram/1024**3
    memory_limit=3 if gb<12 else 5 if gb<24 else 6 if gb<32 else 8
    return max(2,min(8,memory_limit,max(2,cores//2)))


class Scheduler:
    def __init__(self,capacity=None,load=None):
        self.capacity=capacity if capacity is not None else machine_capacity()
        self.reserved=2 if self.capacity>=4 else 1
        self.background_limit=max(1,self.capacity-self.reserved)
        self.condition=threading.Condition()
        self.active={};self.waiting=[];self.sequence=0;self.maintenance=False
        self.load=load or self.heavy_load
    @staticmethod
    def heavy_load():
        try:return os.getloadavg()[0]>(os.cpu_count() or 2)*1.5
        except (AttributeError,OSError):return False
    def snapshot(self):
        with self.condition:
            return {'capacity':self.capacity,'reserved':self.reserved,'running':len(self.active),'queued':len(self.waiting),'maintenance':self.maintenance,'heavy_load':self.load(),'requests':[dict(t,state='running') for t in self.active.values()]+[dict(t,state='queued') for t in self.waiting]}
    @contextmanager
    def slot(self,profile,timeout=180):
        # Search batches outrank automatic scanning; direct interactions outrank both.
        priority=2 if profile in ('tasks','briefing') else 1 if profile=='workspace_search' else 0
        with self.condition:
            if len(self.waiting)>=32:raise RuntimeError('Bob already has many queued requests. Please wait for some to finish.')
            self.sequence+=1;ticket={'id':self.sequence,'profile':profile,'priority':priority}
            self.waiting.append(ticket);self.condition.notify_all();deadline=time.monotonic()+timeout
            try:
                while True:
                    eligible=[t for t in self.waiting if t['priority']==0 or sum(a['priority']>0 for a in self.active.values())<self.background_limit]
                    first=min(eligible,key=lambda t:(t['priority'],t['id'])) if eligible else None
                    under_load=self.load() and priority>0 and bool(self.active)
                    if not self.maintenance and len(self.active)<self.capacity and first is ticket and not under_load:
                        self.waiting.remove(ticket);self.active[ticket['id']]=ticket;self.condition.notify_all();break
                    remaining=deadline-time.monotonic()
                    if remaining<=0:raise RuntimeError('Bob work is queued because this Mac is busy or Bob is being updated. Please retry shortly.')
                    self.condition.wait(min(remaining,1))
            except BaseException:
                if ticket in self.waiting:self.waiting.remove(ticket)
                self.condition.notify_all();raise
        try:yield
        finally:
            with self.condition:self.active.pop(ticket['id'],None);self.condition.notify_all()
    def begin_maintenance(self):
        with self.condition:
            if self.maintenance or self.active or self.waiting:return False
            self.maintenance=True;return True
    def end_maintenance(self):
        with self.condition:self.maintenance=False;self.condition.notify_all()

SCHEDULER=Scheduler()
