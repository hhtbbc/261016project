program solarprobe
use apex,only: subsol
implicit none
real :: lat,lon
integer :: minute
do minute=0,10,5
 call subsol(2023,77,0,minute,0.0,lat,lon)
 write(*,*) minute,lat,lon
enddo
end program
