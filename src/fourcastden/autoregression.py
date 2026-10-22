"""Any-length independent audit of the author's normalized-state autoregression."""
import numpy as np

def check_autoregression(inputs,states,full_real,sw,history=0,raw_outputs=None,flow=False):
    if type(history) is not int or history not in (0,1):raise ValueError('Only official H=0/1 supported')
    length=len(inputs);r=np.asarray(full_real);s=np.asarray(sw)
    if length<1 or len(states)!=length:raise ValueError('Matching positive number of actual forwards required')
    if r.shape!=(length+history+1,177,36,72) or s.shape!=(length+history+1,4):raise ValueError('Complete real frame and scalar sequence required')
    if not np.isfinite(r).all() or not np.isfinite(s).all():raise ValueError('Nonfinite real sequence')
    if flow and history:raise ValueError('Official Flow has no history')
    if raw_outputs is not None and len(raw_outputs)!=length:raise ValueError('Raw forward count differs')
    for i,((x,driver),out) in enumerate(zip(inputs,states)):
        if x.shape!=(1,177*(history+1),36,72) or out.shape!=(1,171,36,72):raise ValueError('Wrong state/input shape')
        if not np.isfinite(x).all() or not np.isfinite(out).all():raise ValueError('Nonfinite actual network state')
        blocks=x.reshape(history+1,177,36,72)
        for j in range(history+1):
            index=i+j
            expected=r[index,:171] if index<=history else states[index-history-1][0]
            np.testing.assert_array_equal(blocks[j,:171],expected)
            np.testing.assert_array_equal(blocks[j,171:],r[index+1,171:])
        np.testing.assert_array_equal(driver.reshape(4),s[i+history+1])
        if raw_outputs is not None:
            expected=raw_outputs[i]+x[:,:171] if flow else raw_outputs[i]
            np.testing.assert_array_equal(out,expected)
    return dict(passed=True,forwards=length,history=history,future_physical_truth_used=False,future_auxiliary_and_scalars_used=True,all_steps_exact=True,flow_delta_checked=flow and raw_outputs is not None,history_after_second_step_is_fully_predicted=bool(history and length>=3))
