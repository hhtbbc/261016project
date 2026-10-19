program gpiread
use gpi_module
use params_module,only: spval
use input_module,only: gpi_ncfile,rd_kp,rd_f107,rd_f107a,rd_power,rd_ctpoten,ntimes_power,ntimes_ctpoten,f107,f107a,power,ctpoten
implicit none
integer :: i
gpi_ncfile='/workspace/data/20261016/data/processed/tiegcm2023/gpi_20230312_20230325.nc'
rd_kp=spval;rd_f107=spval;rd_f107a=spval;rd_power=spval;rd_ctpoten=spval
ntimes_power=0;ntimes_ctpoten=0
call rdgpi
 do i=0,81000,5400
 call getgpi(2023,80,i,0)
 write(*,*) 'CHECK',i,f107,f107a,power,ctpoten
 enddo
end program
