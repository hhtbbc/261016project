"""Audit official H=1 rolling inputs; no alternative network/update equation."""
import numpy as np

def history_feedback_check(inputs,outputs,full_real,sw):
    if len(inputs)!=2 or len(outputs)!=2:raise ValueError('Two actual forwards required')
    r=np.asarray(full_real);s=np.asarray(sw)
    if r.shape!=(4,177,36,72) or s.shape!=(4,4):raise ValueError('Four hourly fields and scalar rows required')
    for i in range(2):
        x,drivers=inputs[i]
        if x.shape!=(1,354,36,72) or outputs[i].shape!=(1,171,36,72):raise ValueError('History checkpoint requires 354 inputs / 171 outputs')
        blocks=x.reshape(2,177,36,72)
        for j in range(2):
            expected=r[i+j,:171] if i+j<=1 else outputs[i+j-2][0]
            np.testing.assert_array_equal(blocks[j,:171],expected)
            np.testing.assert_array_equal(blocks[j,171:],r[i+j+1,171:])
        np.testing.assert_array_equal(drivers.reshape(4),s[i+2])
    return dict(passed=True,ordering='oldest then newest; each state concatenated with next-hour six auxiliaries',first_states=['real00','real01'],second_states=['real01','predicted02'],future_physical_truth_used=False,target_scalar_hours=['02','03'],auxiliary_hours=[['01','02'],['02','03']])
