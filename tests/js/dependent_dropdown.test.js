"use strict";
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('assets/js/app.js', 'utf8');
const option = (value, cat, label) => ({value, dataset:{category:cat}, textContent:label, cloneNode(){return option(this.value, this.dataset.category, this.textContent);}});
const category = {value:'2', dataset:{serviceFilter:'#service'}, listeners:{}, addEventListener(event, listener){this.listeners[event]=listener;}};
const services = {
  options:[option('', '', 'Select'), option('10', '1', 'Electrical'), option('20','2','Plumbing'),option('30','1','Repair')],
  disabled:false,
  _value:'20',
  get value(){return this._value;},
  set value(v){this._value = this.options.some(x=>x.value===v)?v:'';},
  replaceChildren(...next){this.options=next;this._value='';}
};
const document = {
  querySelectorAll(selector){return selector==='[data-service-filter]'?[category]:[];},
  querySelector(selector){return selector==='#service'?services:null;},
  createElement(tag){assert.equal(tag,'option');return option('','','');},
  addEventListener(){},
};
vm.runInNewContext(source, {document, window:{}, location:{}}, {filename:'assets/js/app.js'});
assert.equal(services.disabled,false);
assert.equal(services.value,'20', 'valid previously chosen service survives validation return');
assert.deepEqual(services.options.map(x=>x.value), ['', '20']);
category.value='1'; category.listeners.change();
assert.equal(services.value,'', 'old category selection must clear');
assert.deepEqual(services.options.map(x=>x.value), ['', '10', '30']);
category.value='3'; category.listeners.change();
assert.equal(services.disabled,true);
assert.equal(services.options[0].textContent, 'No services available in this category');
category.value=''; category.listeners.change();
assert.equal(services.disabled,true);
assert.equal(services.options[0].textContent,'Select a category first');
console.log('PASS dependent dropdown rebuild, selection preservation, and empty states');
