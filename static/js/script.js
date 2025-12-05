document.addEventListener('DOMContentLoaded', function(){
  const venueSelect = document.getElementById('venue-select');
  const dateSelect = document.getElementById('date-select');
  if(window.EVENT_AVAILABLE_DATES && venueSelect){
    venueSelect.addEventListener('change', function(){
      const v = this.value;
      dateSelect.innerHTML = '<option value="">Select date</option>';
      if(v && window.EVENT_AVAILABLE_DATES[v]){
        window.EVENT_AVAILABLE_DATES[v].forEach(function(dt){
          const opt = document.createElement('option');
          opt.value = dt; opt.textContent = dt;
          dateSelect.appendChild(opt);
        });
      }
    });
  }
  const validateBtn = document.getElementById('validate-json');
  if(validateBtn){
    validateBtn.addEventListener('click', function(e){
      const ta = document.querySelector('textarea[name="available_dates"]');
      const text = ta ? ta.value : '';
      fetch('/_validate_dates', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:'text='+encodeURIComponent(text)})
        .then(r=>r.json()).then(j=>{
          if(j.ok){
            alert('JSON looks valid');
          } else {
            alert('Invalid JSON: '+j.error);
          }
        }).catch(err=>{ alert('Validation failed: '+err); });
    });
  }
});
