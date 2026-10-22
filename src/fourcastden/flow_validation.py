"""Independent checks of the author's normalized-space Flow accumulation."""
import numpy as np

def flow_feedback_check(inputs, increments, real, pred, sw):
    if len(inputs)!=2 or len(increments)!=2:
        raise ValueError('Exactly two Flow forwards required')
    np.testing.assert_array_equal(inputs[0][0][0,:171],real[0,:171])
    for k in range(2):
        state=inputs[k][0][0,:171]
        delta=increments[k][0]
        if state.shape!=delta.shape:raise ValueError('Channel/shape mismatch')
        expected=np.add(state,delta,dtype=np.float32)
        np.testing.assert_array_equal(pred[k+1],expected)
        np.testing.assert_array_equal(inputs[k][0][0,171:],real[k+1,171:])
        np.testing.assert_array_equal(inputs[k][1].reshape(-1),sw[k+1])
    np.testing.assert_array_equal(inputs[1][0][0,:171],pred[1])
    return dict(passed=True,normalized_increment_accumulation_exact=True,
                second_input_equals_first_accumulated_prediction=True,
                future_physical_truth_fed=False,future_auxiliary_conditions_used=True)
