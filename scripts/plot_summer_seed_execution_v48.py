"""Use frozen plots with the verified recovery B resource receipt."""
import plot_summer_seed_sensitivity_v46 as legacy
import preflight_summer_seed_recovery_v47 as recovery


def main():
    result = recovery.OUT/'comparison'
    if not recovery.load(result/'independent.json')['verified']:
        raise ValueError('Independent comparison is required before plotting')
    original = legacy.load
    old_b = recovery.OLD/recovery.v46.B/'status.json'

    def load_with_recovered_resource(path):
        return original(recovery.RUN/'status.json' if path == old_b else path)

    legacy.RESULT = result
    legacy.load = load_with_recovered_resource
    legacy.main()
    snapshots = [r for r in legacy.table('hourly')
                 if r['region']=='global' and r['hour'] in ('24','72','168','336')]
    f, axes = legacy.plt.subplots(2, 2, figsize=(10,6))
    for ax,key,metric,scale,unit in zip(axes.ravel(),
             ('DEN','TN','WIND_VECTOR','HE'),('relative_P95','RMSE','RMSE','relative_P95'),
             (100,1,.01,100),('%','K','m/s','%')):
        rows = [r for r in snapshots if r['variable']==key]
        ax.bar([int(r['hour'])//24 for r in rows],[float(r[metric])*scale for r in rows])
        ax.set_xticks([1,3,7,14])
        ax.set_ylabel(f'{key} ({unit})')
        ax.set_xlabel("预热日龄")
        ax.set_title(f"{'ilev' if key=='DEN' else 'lev'}；共同有效 n={rows[0]['n']}")
    legacy.label(f,'第 1、3、7、14 天：全球物理场快照',
        '2022-06-08 / 10 / 14 / 21 00Z；junsol − mareqx；DEN、HE 相对 P95；TN、风矢量 RMS；工程 HINDCAST')
    f.savefig(result/'11.png',dpi=130)
    legacy.plt.close(f)


if __name__ == '__main__':
    main()
