program test
use apex, only: cofrm,feldg
implicit none
real :: d,x,y,z,bx,by,bz,b
integer :: i,j
 do i=1,2
 d=2002.2
 if(i==2)d=2023.2
 call cofrm(d)
 do j=1,3
 x=0.7+j*0.1; y=0.2; z=0.4
 call feldg(2,x,y,z,bx,by,bz,b)
 write(*,*) d,x,y,z,bx,by,bz,b
 enddo
 enddo
end program
