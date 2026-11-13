"""Layout-only revision; preserve first image and all scientific values."""
from pathlib import Path
import sys,json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_tiegcm_2022_b14_v2 import F,O
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
 old=O/'multivariable_acceptance.png';draft=O/'figure_draft_local';draft.mkdir()
 shutil.copy2(old,draft/'multivariable_acceptance_v1.png')
 q=json.loads((O/'delta14/summary.json').read_text());variables=['DEN','TN','WIND_VECTOR','O1','O2','N2','HE'];periods=['candidate','last24h','endpoint'];matrix=np.array([[q['gates'][p][v]['failed_cells'] for p in periods] for v in variables])
 fig,ax=plt.subplots(figsize=(8,5.4));ax.imshow(matrix>0,aspect='auto',cmap=matplotlib.colors.ListedColormap(['#c3e5dd','#efaaa1']),vmin=0,vmax=1)
 for i in range(len(variables)):
  for j in range(3):ax.text(j,i,('PASS' if matrix[i,j]==0 else 'FAIL')+'\n'+str(matrix[i,j]),ha='center',va='center')
 ax.set_xticks(range(3),['Candidate\n49 frames','Last 24 h\n25 frames','Endpoint\nMar25 00 UTC']);ax.set_yticks(range(7),variables);ax.set_title('2022 14-day native-layer frozen gates / failed cells')
 fig.text(.5,.006,'EXPLORATORY v2 / 2022 A14 ENGINEERING PARTIAL / B14 PASS / PROVISIONAL HINDCAST',ha='center',fontsize=8);fig.tight_layout(rect=(0,.045,1,1));fig.savefig(old,dpi=155);plt.close(fig)
 (F/'layout_revision.json').open('x').write(json.dumps(dict(reason='First acceptance matrix x labels overlapped due equal image aspect',numerical_changes=False,first_image_SHA256=sha(draft/'multivariable_acceptance_v1.png'),final_image_SHA256=sha(old),source_SHA256=sha(Path(__file__)),original_preserved_local=True),indent=2))
 print('Layout fixed; numerical data unchanged')
